"""Import manually downloaded official store metrics to SEPARATE store-only SQLite.

Input: user-prepared normalized CSV from an official publisher report, header:
store,app_id,report_date,metric,downloads,source_report
Never guesses installs from QR scans; does not touch timetable.db.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import sqlite3
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS official_store_metrics (
    store TEXT NOT NULL, app_id TEXT NOT NULL, report_date TEXT NOT NULL,
    metric TEXT NOT NULL, downloads INTEGER NOT NULL, source_report TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    PRIMARY KEY (store,app_id,report_date,metric)
)"""


def import_csv(source: Path, dest: Path) -> int:
    source = source.expanduser().resolve(strict=True)
    dest = dest.expanduser().resolve()
    if source == dest or dest.name.casefold() == "timetable.db":
        raise ValueError("Store data must be a SEPARATE database, never timetable.db")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("No rows. Prepare official data in the documented CSV format.")
    payload = []
    for row in rows:
        store = (row.get("store") or "").strip()
        app_id = (row.get("app_id") or "").strip()
        day = (row.get("report_date") or "").strip()
        metric = (row.get("metric") or "").strip()
        proof = (row.get("source_report") or "").strip()
        val = (row.get("downloads") or "").strip()
        if store not in {"Google Play", "Apple App Store"} or not app_id or not metric or not proof:
            raise ValueError("Each row needs a valid store, app_id, metric and source_report.")
        import datetime
        datetime.date.fromisoformat(day)
        count = int(val)
        if count < 0:
            raise ValueError("Downloads must not be negative.")
        payload.append((store, app_id, day, metric, count, proof, digest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dest) as db:
        db.execute(SCHEMA)
        # Source rows replace matching app/day/metric, never double count overlapping exports.
        db.executemany("INSERT INTO official_store_metrics VALUES (?,?,?,?,?,?,?) "
                       "ON CONFLICT(store,app_id,report_date,metric) DO UPDATE SET "
                       "downloads=excluded.downloads,source_report=excluded.source_report,"
                       "source_sha256=excluded.source_sha256", payload)
    return len(payload)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--file", type=Path, required=True, help="Verified normalized publisher report CSV")
    p.add_argument("--db", type=Path, required=True, help="Separate store metrics sqlite3 file")
    args = p.parse_args()
    print(f"Imported {import_csv(args.file,args.db)} official publisher report rows into {args.db}")
