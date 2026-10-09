"""Read-only QR geo/device and verified store report endpoints.

Additive router: include this APIRouter inside the existing /api/v1 router.
No changes to QR redirection, KV, or the QR database schema.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from ..database import Database
from ..dependencies import get_database

router = APIRouter(tags=["QR Reporting v3"])
UNKNOWN = "Unknown"
MAX_GROUPS = 1000


def _read_connection(database: Database) -> sqlite3.Connection:
    # Use the exact active Database object, never guess between the root/service DB.
    uri = Path(database.path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def _scope(database: Database, qr_id: str | None):
    if qr_id and database.get_qr_code(qr_id) is None:
        raise HTTPException(status_code=404, detail="QR not found")
    return "s.confirmed=1" + (" AND s.qr_id=?" if qr_id else ""), ([qr_id] if qr_id else [])


def _geo_expr(key: str) -> str:
    # Cloudflare region/city are present for new KV-based scan events.
    # Cloudflare does not provide a dependable district field.
    return (
        "COALESCE(NULLIF(TRIM(CAST(CASE WHEN json_valid(s.telemetry_json) "
        f"THEN json_extract(s.telemetry_json, '$.edge.{key}') END AS TEXT)),''),'Unknown')"
    )


def _read_rows(con: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def _report(database: Database, qr_id: str | None):
    where, params = _scope(database, qr_id)
    geo_state, geo_city = _geo_expr("region"), _geo_expr("city")
    # This field is intentionally not replaced with city: city != district.
    geo_district = _geo_expr("district")
    with _read_connection(database) as con:
        total = _read_rows(con, f"""
            SELECT COUNT(*) scans, COUNT(DISTINCT NULLIF(s.visitor_hash,'')) unique_browsers
            FROM qr_scans s WHERE {where}
        """, params)[0]
        locations = _read_rows(con, f"""
            SELECT COALESCE(NULLIF(s.country,''),'Unknown') country,
              {geo_state} state, {geo_district} district, {geo_city} city,
              COUNT(*) scans, COUNT(DISTINCT NULLIF(s.visitor_hash,'')) unique_browsers
            FROM qr_scans s WHERE {where}
            GROUP BY country, state, district, city
            ORDER BY scans DESC LIMIT ?
        """, [*params, MAX_GROUPS])
        devices = _read_rows(con, f"""
            SELECT substr(s.visitor_hash,1,12) device_token,
              COALESCE(NULLIF(s.device_type,''),'Unknown') device_type,
              COALESCE(NULLIF(s.operating_system,''),'Unknown') operating_system,
              COALESCE(NULLIF(s.browser,''),'Unknown') browser,
              COALESCE(NULLIF(s.device_model,''),'Unknown') device_model,
              COUNT(*) scans, MIN(s.scanned_at) first_seen, MAX(s.scanned_at) last_seen,
              COUNT(DISTINCT s.qr_id) qr_campaigns
            FROM qr_scans s WHERE {where}
            GROUP BY s.visitor_hash
            ORDER BY scans DESC LIMIT ?
        """, [*params, MAX_GROUPS])
        qr_codes = _read_rows(con, f"""
            SELECT s.qr_id, COALESCE(c.name,'Unknown') qr_name, COUNT(*) scans,
              COUNT(DISTINCT NULLIF(s.visitor_hash,'')) unique_browsers
            FROM qr_scans s LEFT JOIN qr_codes c ON c.id=s.qr_id
            WHERE {where}
            GROUP BY s.qr_id,c.name ORDER BY scans DESC LIMIT ?
        """, [*params, MAX_GROUPS])
    return {
        "qr_id": qr_id, "verified_scans": total["scans"],
        "unique_browsers": total["unique_browsers"],
        "location_quality": "Approximate Cloudflare IP geolocation; district only when independently supplied",
        "device_quality": "Browser-scoped pseudonymous token; not a guaranteed physical device ID",
        "locations": locations, "devices": devices, "qr_codes": qr_codes,
        "limited_to_top_groups": MAX_GROUPS,
    }


@router.get("/qr-reports/summary")
def summary(qr_id: str | None = Query(default=None), database: Database = Depends(get_database)):
    return _report(database, qr_id)


def _clean_csv(value):
    text = str(value if value is not None else "")
    # Prevent Excel formula execution when exporting arbitrary device/location labels.
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@router.get("/qr-reports/scans.csv")
def export_scans(qr_id: str | None = Query(default=None), database: Database = Depends(get_database)):
    where, params = _scope(database, qr_id)
    state, city, district = _geo_expr("region"), _geo_expr("city"), _geo_expr("district")
    sql = f"""
      SELECT c.name qr_name, s.scanned_at, s.country, {state} state,
       {district} district, {city} city, s.device_type, s.operating_system,
       s.browser, s.device_model, substr(s.visitor_hash,1,12) device_token
      FROM qr_scans s LEFT JOIN qr_codes c ON c.id=s.qr_id
      WHERE {where} ORDER BY s.scanned_at DESC
    """
    def generate():
        # Stream: do not load millions of scan records into web/app memory.
        fields = ["qr_name","scanned_at","country","state","district","city",
                  "device_type","operating_system","browser","device_model","device_token"]
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(fields)
        yield "\ufeff" + out.getvalue()
        with _read_connection(database) as con:
            cursor = con.execute(sql, params)
            while True:
                batch = cursor.fetchmany(2000)
                if not batch:
                    break
                out.seek(0)
                out.truncate(0)
                for row in batch:
                    writer.writerow([_clean_csv(row[f]) for f in fields])
                yield out.getvalue()
    filename = "qr-verified-geolocation-and-device-scans.csv"
    return StreamingResponse(generate(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',"Cache-Control":"no-store"})


@router.get("/qr-reports/summary.pdf")
def export_pdf(qr_id: str | None = Query(default=None), database: Database = Depends(get_database)):
    data = _report(database, qr_id)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF support requires reportlab in the API environment")
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50
    def line(value, size=9):
        nonlocal y
        if y < 52:
            pdf.showPage()
            y = height - 50
        pdf.setFont("Helvetica", size)
        # Helvetica core PDF font is Latin-1 only. Replace unsupported glyphs.
        pdf.drawString(42, y, str(value).encode("latin-1", "replace").decode("latin-1")[:108])
        y -= 15
    line("NextToppers | QR Analytics", 16)
    line(f"Generated UTC: {datetime.now(timezone.utc).isoformat()}")
    line(f"QR filter: {qr_id or 'All QR codes'}")
    line(f"Verified scans: {data['verified_scans']} | Unique browsers: {data['unique_browsers']}", 11)
    line("Note: State/city are approximate IP geography. Unknown district is not guessed.")
    line("Note: Browser tokens are not physical device serial numbers.")
    for label, keys, limit in (
        ("Location breakdown", ("country","state","district","city","scans"), 75),
        ("Top devices", ("device_token","device_type","operating_system","browser","scans"), 75),
        ("QR breakdown", ("qr_name","scans","unique_browsers"), 75),
    ):
        y -= 10
        line(label, 12)
        for row in data[{"Location breakdown":"locations","Top devices":"devices","QR breakdown":"qr_codes"}[label]][:limit]:
            line(" | ".join(str(row.get(key, UNKNOWN)) for key in keys))
    pdf.save()
    return Response(content=buf.getvalue(), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="qr-analytics-report.pdf"',
                 "Cache-Control":"no-store"})


def _store_db(database: Database) -> Path:
    value = os.environ.get("NEXTTOPPERS_QR_STORE_REPORT_DB", "").strip()
    return Path(value).expanduser().resolve() if value else Path(database.path).parent / "qr_store_reports_v3.sqlite3"


@router.get("/qr-reports/stores")
def store_stats(database: Database = Depends(get_database)):
    """Imported official aggregated store metrics; never silently attribute to a QR."""
    path = _store_db(database)
    response = {"status": "not_connected", "verified_store_downloads": [],
                "note": "Store aggregates are not QR-attributed installs. Import official console reports."}
    if not path.is_file():
        return response
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
    con.row_factory = sqlite3.Row
    try:
        rows = _read_rows(con, """
            SELECT store,app_id,kind,SUM(count) count,MAX(report_date) latest_date
            FROM official_downloads GROUP BY store,app_id,kind ORDER BY store,app_id,kind
        """)
        response.update(status="imported_official_reports", verified_store_downloads=rows)
    finally:
        con.close()
    return response
