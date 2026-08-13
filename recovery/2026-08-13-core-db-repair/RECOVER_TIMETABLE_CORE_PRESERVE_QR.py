from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TRUSTED = {
    "Humanities": "1M8mxrLzxZ9AixQ7fejbzIjhZGLgNzS7flMx6cXgiXHQ",
    "Science": "1j1yR4DRzqJwnkkfHmeWuv7vP-iDP0KZVahV4l9lcjEg",
    "Commerce": "1vEGv2nzGYlFWtHT8SmvzGIYeL_Yl9RJNRohM2VHY0Lg",
    "Nirmaan": "1a7qJpddbGL3fnR6RBmsrFxqjjVLB_g9Ryz7cQ1i0W8U",
}
QR_TABLES = ("qr_templates", "qr_codes", "qr_scans")
CORE_TABLES = ("sources", "timetable_entries", "changes", "test_records", "content_items", "workbook_profiles")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def log(report: str | None, line: str = "") -> None:
    print(line, flush=True)
    if report:
        path = Path(report)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def connect_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=20)


def table_names(conn: sqlite3.Connection, schema: str = "main") -> set[str]:
    return {row[0] for row in conn.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")}


def count(conn: sqlite3.Connection, table: str, schema: str = "main") -> int | None:
    if table not in table_names(conn, schema):
        return None
    return int(conn.execute(f'SELECT COUNT(*) FROM {schema}."{table}"').fetchone()[0])


def summary(path: Path) -> dict[str, Any]:
    conn = connect_ro(path)
    try:
        out: dict[str, Any] = {
            "path": str(path),
            "size": path.stat().st_size,
            "integrity": conn.execute("PRAGMA integrity_check").fetchone()[0],
        }
        for table in (*CORE_TABLES, *QR_TABLES):
            out[table] = count(conn, table)
        if "sources" in table_names(conn):
            cols = [r[1] for r in conn.execute("PRAGMA table_info(sources)").fetchall()]
            wanted = [c for c in ("id", "name", "spreadsheet_id", "enabled", "last_sync_status", "last_sync_at", "last_error") if c in cols]
            if wanted:
                sql = "SELECT " + ",".join(f'"{c}"' for c in wanted) + " FROM sources"
                out["sources_detail"] = [dict(zip(wanted, row)) for row in conn.execute(sql).fetchall()]
        return out
    finally:
        conn.close()


def sqlite_backup(src_path: Path, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    src = connect_ro(src_path)
    dst = sqlite3.connect(dest_path, timeout=30)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


def columns(conn: sqlite3.Connection, table: str, schema: str = "main") -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA {schema}.table_info("{table}")').fetchall()]


def create_sql(conn: sqlite3.Connection, table: str, schema: str) -> str | None:
    row = conn.execute(f"SELECT sql FROM {schema}.sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return str(row[0]) if row and row[0] else None


def ensure_dest_table(conn: sqlite3.Connection, table: str) -> None:
    if table in table_names(conn, "main"):
        return
    sql = create_sql(conn, table, "qr_src")
    if not sql:
        raise RuntimeError(f"Source QR table {table} has no CREATE SQL")
    conn.execute(sql)


def merge_table(conn: sqlite3.Connection, table: str) -> tuple[int, int, int]:
    if table not in table_names(conn, "qr_src"):
        return 0, 0, 0
    ensure_dest_table(conn, table)
    src_cols = set(columns(conn, table, "qr_src"))
    dst_cols = columns(conn, table, "main")
    common = [c for c in dst_cols if c in src_cols]
    if not common:
        raise RuntimeError(f"No common columns for {table}")
    quoted = ",".join(f'"{c}"' for c in common)
    before = count(conn, table, "main") or 0
    source_count = count(conn, table, "qr_src") or 0
    conn.execute(f'INSERT OR REPLACE INTO main."{table}" ({quoted}) SELECT {quoted} FROM qr_src."{table}"')
    after = count(conn, table, "main") or 0
    return before, source_count, after


def copy_assets(root: Path, report: str | None) -> None:
    src = root / "data" / "qr_assets"
    dst = root / "services" / "api" / "data" / "qr_assets"
    if not src.exists():
        log(report, f"QR assets: nothing to copy from {src}")
        return
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    present = 0
    for path in src.glob("*.png"):
        target = dst / path.name
        if target.exists():
            present += 1
        else:
            shutil.copy2(path, target)
            copied += 1
    log(report, f"QR assets merged: copied={copied} already_present={present}")


def http_json(api: str, method: str, path: str, timeout: int = 30) -> tuple[int, Any, str]:
    url = path if path.startswith("http") else api.rstrip("/") + path
    data = b"" if method.upper() in {"POST", "PUT", "PATCH", "DELETE"} else None
    req = urllib.request.Request(url, data=data, method=method.upper(), headers={"Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            text = raw.decode("utf-8", errors="replace")
            try:
                body = json.loads(text) if text else None
            except json.JSONDecodeError:
                body = None
            return response.status, body, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text) if text else None
        except json.JSONDecodeError:
            body = None
        return exc.code, body, text
    except Exception as exc:
        return 0, None, f"{type(exc).__name__}: {exc}"


def items(body: Any) -> list[dict[str, Any]]:
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if isinstance(body, dict):
        for key in ("items", "data", "results", "sources"):
            value = body.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def api_count(api: str, path: str) -> int | None:
    status, body, _ = http_json(api, "GET", path, 20)
    if status != 200:
        return None
    if isinstance(body, list):
        return len(body)
    if isinstance(body, dict):
        if isinstance(body.get("total"), int):
            return int(body["total"])
        return len(items(body))
    return 0


def inspect(ns: argparse.Namespace) -> int:
    core = summary(Path(ns.core_db))
    qr = summary(Path(ns.qr_db))
    log(ns.report, "CORE DB READ-ONLY SUMMARY")
    log(ns.report, json.dumps(core, indent=2, default=str))
    log(ns.report, "ROOT/QR DB READ-ONLY SUMMARY")
    log(ns.report, json.dumps(qr, indent=2, default=str))
    if core["integrity"] != "ok" or qr["integrity"] != "ok":
        log(ns.report, "FAIL: SQLite integrity_check failed")
        return 3
    if int(core.get("sources") or 0) <= 0:
        log(ns.report, "FAIL: service/API DB has no sources; automatic recovery stops")
        return 4
    if core.get("timetable_entries") is None:
        log(ns.report, "FAIL: service/API DB has no timetable_entries table")
        return 5
    log(ns.report, "PASS: service/API DB contains timetable/source core and both DBs are valid")
    return 0


def backup(ns: argparse.Namespace) -> int:
    backup_dir = Path(ns.backup_dir)
    sqlite_backup(Path(ns.core_db), backup_dir / "services_api_data_timetable.db")
    sqlite_backup(Path(ns.qr_db), backup_dir / "root_data_timetable.db")
    log(ns.report, f"PASS consistent DB backups created in {backup_dir}")
    return 0


def merge(ns: argparse.Namespace) -> int:
    core = Path(ns.core_db)
    qr = Path(ns.qr_db)
    pre_qr = summary(qr)
    conn = sqlite3.connect(core, timeout=30)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("ATTACH DATABASE ? AS qr_src", (str(qr),))
        conn.execute("BEGIN IMMEDIATE")
        for table in QR_TABLES:
            if table not in table_names(conn, "qr_src"):
                log(ns.report, f"QR merge {table}: source table absent - skipped")
                continue
            before, source_count, after = merge_table(conn, table)
            log(ns.report, f"QR merge {table}: core_before={before} root_source={source_count} core_after={after}")
        duplicate_slugs = []
        if "qr_codes" in table_names(conn):
            duplicate_slugs = conn.execute("SELECT slug,COUNT(*) FROM qr_codes GROUP BY slug HAVING COUNT(*)>1").fetchall()
        if duplicate_slugs:
            raise RuntimeError(f"Duplicate QR slugs after merge: {duplicate_slugs[:10]}")
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise RuntimeError(f"foreign_key_check returned {len(fk)} violations: {fk[:5]}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.execute("DETACH DATABASE qr_src")
        except Exception:
            pass
        conn.close()
    copy_assets(Path(ns.root), ns.report)
    post = summary(core)
    root_qr = int(pre_qr.get("qr_codes") or 0)
    if root_qr and int(post.get("qr_codes") or 0) < root_qr:
        log(ns.report, f"FAIL: merged QR count {post.get('qr_codes')} is below root source count {root_qr}")
        return 6
    log(ns.report, "PASS: only QR tables/assets were merged; timetable/source core was not copied from root DB")
    return 0


def verify_runtime(ns: argparse.Namespace) -> int:
    core = summary(Path(ns.core_db))
    status, source_body, text = http_json(ns.api, "GET", "/api/v1/sources", 20)
    if status != 200:
        log(ns.report, f"FAIL /sources HTTP {status}: {text[:500]}")
        return 7
    status, qr_body, text = http_json(ns.api, "GET", "/api/v1/qr-codes", 20)
    if status != 200:
        log(ns.report, f"FAIL /qr-codes HTTP {status}: {text[:500]}")
        return 8
    api_sources = items(source_body)
    api_qr = items(qr_body)
    expected_sources = int(core.get("sources") or 0)
    expected_qr = int(core.get("qr_codes") or 0)
    log(ns.report, f"Runtime DB check: API sources={len(api_sources)} core sources={expected_sources}")
    log(ns.report, f"Runtime DB check: API QR={len(api_qr)} core QR={expected_qr}")
    if len(api_sources) != expected_sources or len(api_qr) != expected_qr:
        log(ns.report, "FAIL: runtime counts do not match services/api/data/timetable.db")
        return 9
    log(ns.report, "PASS: runtime API matches authoritative service/API DB")
    return 0


def spreadsheet_id(src: dict[str, Any]) -> str:
    if src.get("spreadsheet_id"):
        return str(src["spreadsheet_id"])
    url = str(src.get("url") or "")
    marker = "/spreadsheets/d/"
    return url.split(marker, 1)[1].split("/", 1)[0] if marker in url else ""


def source_id(src: dict[str, Any]) -> str:
    return str(src.get("id") or src.get("source_id") or src.get("sourceId") or "")


def sync(ns: argparse.Namespace) -> int:
    status, body, text = http_json(ns.api, "GET", "/api/v1/sources", 20)
    if status != 200:
        log(ns.report, f"FAIL source list HTTP {status}: {text[:500]}")
        return 11
    sources = items(body)
    by_sheet = {spreadsheet_id(src): src for src in sources if spreadsheet_id(src)}
    missing = [(name, sid) for name, sid in TRUSTED.items() if sid not in by_sheet]
    if missing:
        log(ns.report, "FAIL trusted timetable sources missing from authoritative DB")
        for name, sid in missing:
            log(ns.report, f"  {name}: {sid}")
        return 12
    log(ns.report, "PASS all four trusted timetable Google Sheet sources are present")

    failures = 0
    for name, sid in TRUSTED.items():
        source = by_sheet[sid]
        internal_id = source_id(source)
        path = f"/api/v1/sources/{urllib.parse.quote(internal_id, safe='')}/sync"
        log(ns.report, f"Syncing {name} via {path}")
        status, _, text = http_json(ns.api, "POST", path, 150)
        if status != 200:
            log(ns.report, f"FAIL {name}: HTTP {status}: {text[:800]}")
            failures += 1
        else:
            log(ns.report, f"PASS {name}: HTTP 200")
    if failures:
        return 13

    today = dt.datetime.now(IST).date().isoformat()
    total_path = "/api/v1/timetable?" + urllib.parse.urlencode({"page": 1, "page_size": 500, "class_date": today, "latest": "false", "upcoming": "false"})
    total = api_count(ns.api, total_path)
    log(ns.report, f"Today {today} total timetable rows: {total}")
    for stream in ("Commerce", "Science", "Humanities", "Nirmaan"):
        path = "/api/v1/timetable?" + urllib.parse.urlencode({"page": 1, "page_size": 500, "class_date": today, "stream": stream, "latest": "false", "upcoming": "false"})
        log(ns.report, f"  {stream}: {api_count(ns.api, path)}")

    for path in (
        "/api/v1/dashboard",
        "/api/v1/changes?page=1&page_size=1&period=today&view=cells",
        "/api/v1/test-monitor?compact=true",
        "/api/v1/qr-codes",
    ):
        status, _, text = http_json(ns.api, "GET", path, 30)
        log(ns.report, f"Endpoint {path}: HTTP {status}")
        if status != 200:
            log(ns.report, f"FAIL endpoint: {text[:500]}")
            return 16
    if total is None or total <= 0:
        log(ns.report, "FAIL: Google Sheets synced but Today timetable is empty")
        return 18
    final = summary(Path(ns.core_db))
    log(ns.report, f"Final core DB: sources={final.get('sources')} timetable_entries={final.get('timetable_entries')} qr_codes={final.get('qr_codes')} qr_scans={final.get('qr_scans')} qr_templates={final.get('qr_templates')}")
    log(ns.report, "PASS Google Sheet sync + Today + Test Monitor + Sheet Updates + QR runtime checks")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("inspect", "backup", "merge", "verify-runtime", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--core-db", required=True)
        p.add_argument("--report")
        if name in {"inspect", "backup", "merge"}:
            p.add_argument("--qr-db", required=True)
        if name == "backup":
            p.add_argument("--backup-dir", required=True)
        if name == "merge":
            p.add_argument("--root", required=True)
        if name in {"verify-runtime", "sync"}:
            p.add_argument("--api", required=True)
    ns = parser.parse_args()
    try:
        return {
            "inspect": inspect,
            "backup": backup,
            "merge": merge,
            "verify-runtime": verify_runtime,
            "sync": sync,
        }[ns.cmd](ns)
    except Exception as exc:
        log(getattr(ns, "report", None), f"UNEXPECTED FAIL: {type(exc).__name__}: {exc}")
        return 90


if __name__ == "__main__":
    raise SystemExit(main())
