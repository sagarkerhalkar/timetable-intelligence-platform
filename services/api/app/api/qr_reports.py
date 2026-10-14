"""Read-only QR geo and estimated-device analytics. No redirects or QR writes."""
from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Query, Response

from ..dependencies import get_database

router = APIRouter(prefix="/api/v1/qr-reports", tags=["qr-reports"])
PERIODS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365, "all": None}
DATA_SECTIONS = {"locations", "devices", "types"}


def _date_clause(period: str, qr_id: str) -> tuple[str, list[str]]:
    conditions = ["s.confirmed=1", "LOWER(COALESCE(s.device_type,''))!='bot'"]
    params: list[str] = []
    if PERIODS[period] is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=PERIODS[period])
        conditions.append("s.scanned_at>=?")
        params.append(cutoff.isoformat())
    if qr_id:
        conditions.append("s.qr_id=?")
        params.append(qr_id)
    return " AND ".join(conditions), params


def _geo_field(field: str) -> str:
    # Only approximate city and state supplied by edge telemetry; no district.
    if field not in {"region", "city"}:
        raise ValueError("Unsupported location dimension")
    return (
        "COALESCE(NULLIF(TRIM(CASE WHEN json_valid(s.telemetry_json) "
        f"THEN CAST(json_extract(s.telemetry_json,'$.edge.{field}') AS TEXT) END),''),'Unknown')"
    )


def _query_rows(connection: sqlite3.Connection, query: str, params: list | tuple = ()) -> list[dict]:
    return [dict(row) for row in connection.execute(query, params).fetchall()]


def _report(connection: sqlite3.Connection, period: str, qr_id: str) -> dict:
    if qr_id and not connection.execute("SELECT 1 FROM qr_codes WHERE id=?", (qr_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Unknown QR")
    where, params = _date_clause(period, qr_id)
    base = "FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id"
    total = int(connection.execute(f"SELECT COUNT(*) {base} WHERE {where}", params).fetchone()[0])
    # A visitor_hash represents a browser-profile visitor ID persisted by the QR landing page.
    # A phone with Chrome and Safari, or a private tab, can generate multiple such IDs.
    # Therefore this is an ESTIMATE of distinct devices, never a physical hardware count.
    unique = int(connection.execute(
        f"SELECT COUNT(DISTINCT NULLIF(TRIM(s.visitor_hash),'')) {base} WHERE {where}", params
    ).fetchone()[0])
    locations = _query_rows(connection, f"""
       SELECT COALESCE(NULLIF(TRIM(s.country),''),'Unknown') AS country,
         {_geo_field('region')} AS state_region,
         {_geo_field('city')} AS city,
         COUNT(*) AS scans,
         COUNT(DISTINCT NULLIF(TRIM(s.visitor_hash),'')) AS estimated_devices
       {base} WHERE {where}
       GROUP BY country,state_region,city ORDER BY scans DESC LIMIT 200
       """, params)
    types = _query_rows(connection, f"""
       SELECT COALESCE(NULLIF(s.device_type,''),'Unknown') AS device_type,
         COALESCE(NULLIF(s.operating_system,''),'Unknown') AS operating_system,
         COALESCE(NULLIF(s.browser,''),'Unknown') AS browser,
         COUNT(*) AS scans,
         COUNT(DISTINCT NULLIF(TRIM(s.visitor_hash),'')) AS estimated_devices
       {base} WHERE {where}
       GROUP BY device_type,operating_system,browser ORDER BY scans DESC LIMIT 150
       """, params)
    devices = _query_rows(connection, f"""
       SELECT s.qr_id,q.name AS qr_name,q.slug AS qr_slug, s.visitor_hash AS private_hash,
         COUNT(*) AS scans,MIN(s.scanned_at) AS first_seen_utc,
         MAX(s.scanned_at) AS last_seen_utc,MAX(s.device_type) AS device_type,
         MAX(s.operating_system) AS operating_system,MAX(s.browser) AS browser
       {base} WHERE {where} AND TRIM(COALESCE(s.visitor_hash,''))!=''
       GROUP BY s.qr_id,s.visitor_hash ORDER BY scans DESC, last_seen_utc DESC LIMIT 250
       """, params)
    for device in devices:
        # Never expose original persistent browser-profile hash; saltless re-hashing
        # is only intended for a shortened display label, not an actual hardware ID.
        device["device_id"] = "Device-" + hashlib.sha256(device.pop("private_hash").encode()).hexdigest()[:10].upper()
    return {
        "period": period, "qr_id": qr_id or None, "verified_scans": total,
        "estimated_unique_devices": unique,
        "locations": locations, "device_types": types, "devices": devices,
        "accuracy": {
            "location": "Country/state/city are approximate network-based geo metadata.",
            "devices": "Estimated distinct device browser profiles from persistent anonymous visitor IDs; NOT verified physical hardware, model, or people. Multiple browsers or private mode may count separately.",
        },
        "limits": {"locations": 200, "device_types": 150, "devices": 250,
                   "scope": "Verified, non-bot scans only. Detail rows are capped; totals are not."},
    }


@router.get("/summary")
def summary(period: str = Query("30d"), qr_id: str = Query("", max_length=120)) -> dict:
    if period not in PERIODS:
        raise HTTPException(status_code=422, detail="Invalid period")
    database = get_database()
    with database.connect() as connection:
        return _report(connection, period, qr_id)


def _as_csv(records: list[dict]) -> str:
    stream = io.StringIO(newline="")
    fields = list(records[0]) if records else ["message"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        def neutral(value: object) -> str:
            text = str(value if value is not None else "")
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
        writer.writerow({name: neutral(record.get(name)) for name in fields})
    return stream.getvalue()


@router.get("/export.csv")
def export_csv(period: str = Query("30d"), qr_id: str = Query("", max_length=120),
               section: str = Query("locations")) -> Response:
    if period not in PERIODS or section not in DATA_SECTIONS:
        raise HTTPException(status_code=422, detail="Invalid report filter")
    with get_database().connect() as connection:
        report = _report(connection, period, qr_id)
    name = {"locations": "locations", "devices": "devices", "types": "device_types"}[section]
    rows = report["device_types"] if section == "types" else report[section]
    return Response(content="\ufeff" + _as_csv(rows), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="nexttoppers-{name}-{period}.csv"',
                             "Cache-Control": "no-store"})


@router.get("/export.pdf")
def export_pdf(period: str = Query("30d"), qr_id: str = Query("", max_length=120)) -> Response:
    if period not in PERIODS:
        raise HTTPException(status_code=422, detail="Invalid period")
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    with get_database().connect() as connection:
        data = _report(connection, period, qr_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=34, rightMargin=34, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterBrand", parent=styles["Title"], alignment=TA_CENTER, fontSize=17, leading=21))
    story = [Paragraph("NextToppers | QR Geography & Devices", styles["CenterBrand"]), Spacer(1, 8),
             Paragraph(f"Period: {escape(period)} | Verified scans: {data['verified_scans']:,} | Estimated unique devices: {data['estimated_unique_devices']:,}", styles["BodyText"]),
             Paragraph("Device figures estimate distinct browser profiles, NOT physical phones/computers. City/state are approximate. Counts come from confirmed QR visits.", styles["BodyText"]), Spacer(1, 12)]
    for title, key, columns in (
        ("Geography", "locations", ("country", "state_region", "city", "scans", "estimated_devices")),
        ("Device categories", "device_types", ("device_type", "operating_system", "browser", "scans", "estimated_devices")),
        ("Per-device scan counts (anonymous)", "devices", ("qr_name", "device_id", "scans")),
    ):
        story.append(Paragraph(escape(title), styles["Heading2"]))
        rows = data[key][:20]
        if not rows:
            story.append(Paragraph("No data for this selection.", styles["BodyText"]))
            continue
        cells = [[Paragraph(escape(str(x).replace("_", " ").title()), styles["BodyText"]) for x in columns]]
        for row in rows:
            cells.append([Paragraph(escape(str(row.get(x, ""))[:72]), styles["BodyText"]) for x in columns])
        table = Table(cells, repeatRows=1, hAlign="LEFT", colWidths=[(A4[0]-68)/len(columns)]*len(columns))
        table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#E7EDFA")),
                                   ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#DCE3EB")),
                                   ("VALIGN",(0,0),(-1,-1),"TOP"),
                                   ("TOPPADDING",(0,0),(-1,-1),5),
                                   ("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story.append(table)
        story.append(Spacer(1, 10))
    doc.build(story)
    return Response(content=buffer.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="nexttoppers-qr-insights-{period}.pdf"',
                             "Cache-Control": "no-store"})
