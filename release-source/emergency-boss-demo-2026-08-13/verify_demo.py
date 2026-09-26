from __future__ import annotations
import argparse, json, sqlite3, sys, urllib.request, urllib.error
from pathlib import Path

def db_counts(path: Path):
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def count(t):
            return None if t not in tables else int(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
        return {"integrity": integrity, "sources": count("sources"), "timetable_entries": count("timetable_entries"), "test_records": count("test_records"), "changes": count("changes"), "qr_codes": count("qr_codes"), "qr_scans": count("qr_scans")}
    finally:
        con.close()

def http(url: str):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            body = r.read(); text = body.decode("utf-8", errors="replace")
            try: parsed = json.loads(text) if text else None
            except Exception: parsed = None
            return r.status, parsed, text
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return e.code, None, text
    except Exception as e:
        return 0, None, str(e)

def total_from(body):
    if isinstance(body, dict):
        if isinstance(body.get("total"), int): return body["total"]
        for key in ("items","data","results"):
            if isinstance(body.get(key), list): return len(body[key])
    if isinstance(body, list): return len(body)
    return None

def verify_db(path: Path):
    c = db_counts(path); print("Database counts:", c)
    if c["integrity"] != "ok": return 2
    if (c["sources"] or 0) < 4: return 3
    if (c["timetable_entries"] or 0) < 500: return 4
    if (c["test_records"] or 0) < 500: return 5
    if (c["changes"] or 0) < 1: return 6
    if (c["qr_codes"] or 0) < 24: return 7
    return 0

def pre(db: Path, api: str):
    rc = verify_db(db)
    if rc: return rc
    for path in ("/api/v1/dashboard", "/api/v1/sources", "/api/v1/timetable?page=1&page_size=25"):
        status, body, text = http(api.rstrip("/") + path); print("API", path, status)
        if status != 200:
            print(text[:500]); return 10
    status, body, text = http(api.rstrip("/") + "/api/v1/timetable?page=1&page_size=500")
    if status != 200 or (total_from(body) or 0) < 1:
        print("FAIL timetable API empty:", status, total_from(body), text[:300]); return 11
    print("PASS recovered backend/data."); return 0

def post(db: Path, api: str, web: str):
    rc = pre(db, api)
    if rc: return rc
    for path in ("/", "/timetable?view=today", "/timetable?view=week", "/sources", "/changes", "/tests", "/qr/codes"):
        status, body, text = http(web.rstrip("/") + path); print("WEB", path, status)
        if status < 200 or status >= 400:
            print(text[:500]); return 20
    print("PASS all boss-demo pages."); return 0

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
a = sub.add_parser("pre"); a.add_argument("--db", required=True); a.add_argument("--api", required=True)
b = sub.add_parser("post"); b.add_argument("--db", required=True); b.add_argument("--api", required=True); b.add_argument("--web", required=True)
ns = ap.parse_args()
if ns.cmd == "pre": sys.exit(pre(Path(ns.db), ns.api))
sys.exit(post(Path(ns.db), ns.api, ns.web))
