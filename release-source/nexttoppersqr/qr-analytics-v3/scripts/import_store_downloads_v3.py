"""Import official Play Console and App Store Connect download reports.

This offline-only command deliberately has no unauthenticated upload endpoint.
It cannot prove that a specific QR caused an install.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS official_downloads (
 store TEXT NOT NULL, app_id TEXT NOT NULL, report_date TEXT NOT NULL,
 country TEXT NOT NULL, campaign TEXT NOT NULL, kind TEXT NOT NULL,
 count INTEGER NOT NULL CHECK(count >= 0), updated_source TEXT NOT NULL,
 PRIMARY KEY(store, app_id, report_date, country, campaign, kind)
);
CREATE TABLE IF NOT EXISTS official_report_imports (
 sha256 TEXT PRIMARY KEY, store TEXT NOT NULL, app_id TEXT NOT NULL,
 report_name TEXT NOT NULL, metric_rows INTEGER NOT NULL,
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _fields(row):
    return {str(k).strip(): (v or "").strip() for k, v in row.items() if k is not None}


def _count(value):
    try:
        result = int(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid download count {value!r}") from exc
    if result < 0:
        raise ValueError("Negative download count")
    return result


def _date(value):
    result = date.fromisoformat(str(value).strip())
    return result.isoformat()


def parse_report(path: Path, store: str, expected_app_id: str) -> dict[tuple, int]:
    if store == "play" and not path.name.lower().endswith("_country.csv"):
        raise ValueError("Use ONLY Play Console stats/installs/*_country.csv; mixing dimensions double-counts")
    if store == "apple" and not any(path.name.lower().endswith(x) for x in (".txt.gz",".tsv",".csv",".txt")):
        raise ValueError("Apple report must be an App Store Downloads TSV/CSV or txt.gz segment")
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rb") as probe:
        header = probe.read(4)
    encoding = "utf-16" if header.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    with opener(path, "rt", encoding=encoding, newline="") as f:
        # Google Play exports are often UTF-16; fallback to UTF-8 if needed.
        sample = f.read(2048)
        f.seek(0)
        if store == "play" and not sample:
            raise ValueError("Empty report")
        if store == "apple" and "\t" in sample:
            delimiter = "\t"
        else:
            delimiter = ","
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("Missing report header")
        names = {str(v).strip().lstrip("\ufeff") for v in reader.fieldnames}
        required = ({"Date","Package Name","Country","Daily User Installs"} if store == "play"
                    else {"Date","App Apple Identifier","Download Type","Counts"})
        if not required.issubset(names):
            raise ValueError(f"Wrong {store} report: expected columns {sorted(required)}; got {sorted(names)}")
        result = defaultdict(int)
        for raw in reader:
            item = _fields(raw)
            app_id = item["Package Name" if store=="play" else "App Apple Identifier"]
            if app_id != expected_app_id:
                raise ValueError(f"Unexpected app identifier {app_id!r}")
            when = _date(item["Date"])
            if store == "play":
                country = item["Country"] or "Unknown"
                kind = "Daily User Installs"
                campaign = ""
                count = _count(item["Daily User Installs"])
            else:
                country = item.get("Territory", "") or "Unknown"
                kind = item["Download Type"] or "Unknown Download Type"
                campaign = item.get("Campaign", "")  # Not always available in standard data
                count = _count(item["Counts"])
            result[(store, app_id, when, country, campaign, kind)] += count
        if not result:
            raise ValueError("Report contained no download rows")
        return dict(result)


def import_report(path: Path, store: str, app_id: str, database_file: Path):
    blob = path.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    data = parse_report(path, store, app_id)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(database_file, timeout=10)
    try:
        con.executescript(SCHEMA)
        if con.execute("SELECT 1 FROM official_report_imports WHERE sha256=?", (digest,)).fetchone():
            return "already_imported", len(data)
        # Replacing a dimensional breakdown for a period is safer than adding counts.
        # Never sum reimports or alternative files of the same dates.
        dates = sorted({key[2] for key in data})
        con.execute("BEGIN IMMEDIATE")
        for report_date in dates:
            con.execute("DELETE FROM official_downloads WHERE store=? AND app_id=? AND report_date=?",
                        (store,app_id,report_date))
        con.executemany("""
            INSERT INTO official_downloads
            (store,app_id,report_date,country,campaign,kind,count,updated_source)
            VALUES (?,?,?,?,?,?,?,?)
        """, [(s,a,d,c,m,k,n,digest) for (s,a,d,c,m,k),n in data.items()])
        con.execute("""
            INSERT INTO official_report_imports (sha256,store,app_id,report_name,metric_rows)
            VALUES (?,?,?,?,?)
        """, (digest,store,app_id,path.name,len(data)))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return "imported", len(data)


def main():
    parser = argparse.ArgumentParser(description="Import official app store download reports")
    parser.add_argument("--store",choices=["play","apple"],required=True)
    parser.add_argument("--file",type=Path,required=True)
    parser.add_argument("--app-id",required=True,help="Play package name or numeric Apple App ID")
    parser.add_argument("--db",type=Path,required=True,help="SQLite reporting database (not timetable.db)")
    args = parser.parse_args()
    if args.db.resolve().name == "timetable.db":
        parser.error("Never write official reporting data into timetable.db")
    status,rows = import_report(args.file,args.store,args.app_id,args.db)
    print(f"{status}: {rows} aggregated dimension rows in {args.db}")


if __name__ == "__main__":
    main()
