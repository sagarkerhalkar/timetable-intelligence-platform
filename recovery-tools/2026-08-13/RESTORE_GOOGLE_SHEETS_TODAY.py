from __future__ import annotations

import datetime as dt
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\timetable-intelligence-platform")
DB = ROOT / "data" / "timetable.db"
API = "http://127.0.0.1:3550"
TODAY = "2026-08-13"
STAMP = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"SHEET_SYNC_RECOVERY_{STAMP}"
REPORT = Path.home() / "Desktop" / f"GOOGLE_SHEET_SYNC_RECOVERY_{STAMP}.txt"
log_lines: list[str] = []

def log(msg: str = "") -> None:
    print(msg, flush=True)
    log_lines.append(msg)

def save_report() -> None:
    REPORT.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"\nReport: {REPORT}", flush=True)

def http_json(method: str, path: str, timeout: int = 20):
    url = path if path.startswith("http") else API + path
    data = b"" if method.upper() in {"POST", "PUT", "PATCH"} else None
    req = urllib.request.Request(url, data=data, method=method.upper(), headers={"Accept":"application/json","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", errors="replace")
            try:
                return r.status, json.loads(text) if text else None, text
            except json.JSONDecodeError:
                return r.status, None, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text) if text else None
        except json.JSONDecodeError:
            body = None
        return exc.code, body, text
    except Exception as exc:
        return 0, None, str(exc)

def normalize_list(value):
    if isinstance(value, list): return value
    if isinstance(value, dict):
        for key in ("items","sources","data","results"):
            if isinstance(value.get(key), list): return value[key]
    return []

def sqlite_counts(path: Path):
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def c(t): return None if t not in tables else int(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
        return {"integrity":integrity,"qr_codes":c("qr_codes"),"qr_scans":c("qr_scans"),"sources":c("sources"),"timetable_entries":c("timetable_entries")}
    finally:
        con.close()

def backup_db():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / "timetable.db"
    src = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=10)
    dst = sqlite3.connect(target, timeout=10)
    try:
        src.backup(dst); dst.commit()
    finally:
        dst.close(); src.close()
    log(f"PASS database safety backup: {target}")

def sid(s): return str(s.get("id") or s.get("source_id") or s.get("sourceId") or "")
def sname(s): return str(s.get("name") or s.get("title") or s.get("workbook_name") or sid(s) or "Unknown source")
def sstatus(s): return str(s.get("last_sync_status") or s.get("status") or s.get("sync_status") or "")
def serr(s): return str(s.get("last_error") or s.get("error") or s.get("sync_error") or "")
def enabled(s): return bool(s.get("enabled", True))

def get_sources():
    status, body, text = http_json("GET", "/api/v1/sources", 15)
    if status != 200: raise RuntimeError(f"GET /api/v1/sources failed HTTP {status}: {text[:500]}")
    return normalize_list(body)

def sync_paths(openapi):
    found=[]
    for path, methods in (openapi.get("paths", {}) if isinstance(openapi,dict) else {}).items():
        lower=str(path).lower()
        if "source" in lower and any(w in lower for w in ("sync","refresh","check")) and isinstance(methods,dict) and any(str(k).lower()=="post" for k in methods): found.append(path)
    preferred=["/api/v1/sources/{source_id}/sync","/api/v1/sources/{source_id}/refresh","/api/v1/sources/{source_id}/check","/api/v1/sources/sync-all","/api/v1/sources/refresh-all"]
    out=[]
    for p in preferred+found:
        if p not in out: out.append(p)
    return out

def sub(path, source_id):
    if "{" not in path: return path
    for token in ("{source_id}","{id}","{sourceId}"): path=path.replace(token, urllib.parse.quote(source_id,safe=""))
    return None if "{" in path else path

def trigger_one(source, paths):
    source_id=sid(source)
    for candidate in paths:
        path=sub(candidate, source_id)
        if path is None: continue
        if "{" not in candidate and "all" in path.lower(): continue
        status, body, text=http_json("POST", path, 20)
        if status in (200,201,202,204): return True, f"{path} -> HTTP {status}"
        if status not in (404,405): return False, f"{path} -> HTTP {status}: {body if body is not None else text[:300]}"
    return False, "No usable per-source sync endpoint"

def timetable_count(stream=None):
    params={"page":1,"page_size":500,"class_date":TODAY,"latest":"false","upcoming":"false"}
    if stream: params["stream"]=stream
    status,body,text=http_json("GET","/api/v1/timetable?"+urllib.parse.urlencode(params),20)
    if status!=200: return None, f"HTTP {status}: {text[:300]}"
    if isinstance(body,dict): return int(body.get("total",len(normalize_list(body)))), ""
    if isinstance(body,list): return len(body), ""
    return 0,""

def main():
    log("GOOGLE SHEET + TODAY TIMETABLE RECOVERY")
    before=sqlite_counts(DB)
    log(f"DB integrity={before['integrity']} QR={before['qr_codes']} scans={before['qr_scans']} sources={before['sources']} timetable={before['timetable_entries']}")
    if before["integrity"]!="ok" or before["qr_codes"] is None or int(before["qr_codes"])<24: save_report(); return 4
    if http_json("GET","/api/v1/dashboard",10)[0]!=200: log("FAIL API unhealthy"); save_report(); return 5
    sources=get_sources(); enabled_sources=[s for s in sources if enabled(s)]
    for s in sources: log(f"{sname(s)} | enabled={enabled(s)} | status={sstatus(s)}"+(f" | error={serr(s)}" if serr(s) else ""))
    if not enabled_sources: log("FAIL no enabled sources"); save_report(); return 6
    log(f"Today before sync: {timetable_count()[0]}")
    backup_db()
    status,openapi,text=http_json("GET","/api/openapi.json",15)
    if status!=200 or not isinstance(openapi,dict): log(f"FAIL OpenAPI HTTP {status}: {text[:300]}"); save_report(); return 7
    paths=sync_paths(openapi); log("Sync paths: "+" | ".join(paths))
    queued=0
    for s in enabled_sources:
        ok,msg=trigger_one(s,paths); log(("SYNC queued: " if ok else "SYNC FAIL: ")+sname(s)+" | "+msg); queued += int(ok)
    if queued==0: save_report(); return 8
    deadline=time.time()+240
    while time.time()<deadline:
        time.sleep(3); cur=get_sources(); active=[s for s in cur if enabled(s) and sstatus(s).lower() in {"queued","downloading","analyzing","syncing","running","processing"}]
        if not active: break
    final=get_sources(); errors=0
    for s in final:
        if enabled(s):
            log(f"FINAL {sname(s)} status={sstatus(s)}"+(f" error={serr(s)}" if serr(s) else "")); errors += int(sstatus(s).lower()=="error" or bool(serr(s)))
    total,_=timetable_count(); log(f"Today total after sync: {total}")
    for stream in ("Commerce","Science","Humanities","Nirmaan"): log(f"{stream}: {timetable_count(stream)[0]}")
    after=sqlite_counts(DB); log(f"Post-sync QR={after['qr_codes']} scans={after['qr_scans']} timetable={after['timetable_entries']}")
    if after["qr_codes"]!=before["qr_codes"]: log("FAIL QR count changed"); save_report(); return 9
    if errors: log("FAIL source sync errors - see above"); save_report(); return 10
    if total is None or total<=0: log("FAIL sources completed but Today remains empty"); save_report(); return 11
    log("SUCCESS: Google Sheets synced and Today Timetable has data. QR preserved."); save_report(); return 0

if __name__=="__main__":
    raise SystemExit(main())
