"""NextToppers QR analytics candidate: strictly read-only reports, NO deployment."""
from __future__ import annotations
import argparse
import csv
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote, urlparse

def connect_readonly(filename):
    p = Path(filename).expanduser().resolve(strict=True)
    if not p.is_file():
        raise ValueError("The QR database must be a file.")
    uri = "file:" + quote(str(p).replace("\\", "/"), safe="/:") + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    cols = {r[1] for r in db.execute("PRAGMA table_info(qr_scans)")}
    needed = {"qr_id","visitor_hash","confirmed","device_type","country","operating_system","browser","scanned_at","telemetry_json"}
    if not needed.issubset(cols):
        db.close()
        raise ValueError("Unknown qr_scans schema; refusing to guess or alter data.")
    return db

def safe_csv(v):
    s = "" if v is None else str(v)
    return "'" + s if s.lstrip().startswith(("=","+","-","@")) else s

def where(qr_id):
    return "s.confirmed=1 AND COALESCE(LOWER(s.device_type),'')!='bot'" + (" AND s.qr_id=?" if qr_id else ""), ([qr_id] if qr_id else [])

def region_field(name):
    assert name in ("region","city","district")
    j = f"CASE WHEN json_valid(s.telemetry_json) THEN json_extract(s.telemetry_json,'$.edge.{name}') END"
    return f"COALESCE(NULLIF(TRIM({j}),''),'Unknown')"

def rows(db, query, args=()):
    return [dict(r) for r in db.execute(query, args)]

def summarize(db, qr_id=None, max_devices=50000):
    if not 1 <= max_devices <= 250000:
        raise ValueError("max_devices must be in [1,250000]")
    if qr_id and not db.execute("SELECT 1 FROM qr_codes WHERE id=?", (qr_id,)).fetchone():
        raise ValueError("Unknown QR ID")
    filt,args=where(qr_id)
    joined="FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id"
    total=db.execute(f"SELECT COUNT(*) {joined} WHERE {filt}",args).fetchone()[0]
    geo=rows(db,f"""SELECT COALESCE(NULLIF(TRIM(s.country),''),'Unknown') country,
        {region_field('region')} state_region, {region_field('city')} city,
        {region_field('district')} district, COUNT(*) verified_scans,
        COUNT(DISTINCT NULLIF(s.visitor_hash,'')) anonymous_browsers
        {joined} WHERE {filt} GROUP BY country,state_region,city,district
        ORDER BY verified_scans DESC""",args)
    systems=rows(db,f"""SELECT COALESCE(s.device_type,'Unknown') device_type,
        COALESCE(s.operating_system,'Unknown') operating_system,
        COALESCE(s.browser,'Unknown') browser,COUNT(*) verified_scans
        {joined} WHERE {filt} GROUP BY device_type,operating_system,browser
        ORDER BY verified_scans DESC""",args)
    devices=rows(db,f"""SELECT q.slug qr_slug,q.name qr_name,
        SUBSTR(s.visitor_hash,1,12) browser_id,COUNT(*) verified_scans,
        MIN(s.scanned_at) first_seen_utc,MAX(s.scanned_at) last_seen_utc,
        MAX(s.device_type) device_type,MAX(s.operating_system) operating_system,
        MAX(s.browser) browser {joined} WHERE {filt}
        AND COALESCE(TRIM(s.visitor_hash),'')!=''
        GROUP BY s.qr_id,s.visitor_hash ORDER BY verified_scans DESC LIMIT ?""",args+[max_devices])
    for row in devices:
        row["browser_id"]="Device "+row["browser_id"].upper()
    counts=dict(db.execute(f"SELECT s.qr_id,COUNT(*) {joined} WHERE {filt} GROUP BY s.qr_id",args).fetchall())
    codes=rows(db,"SELECT id,slug,name,target_url FROM qr_codes"+(" WHERE id=?" if qr_id else ""),args if qr_id else ())
    store=[]
    allowed={"play.google.com":"Google Play","apps.apple.com":"Apple App Store","itunes.apple.com":"Apple App Store"}
    for c in codes:
        try:
            url=urlparse(c["target_url"])
            provider=allowed.get((url.hostname or "").lower()) if url.scheme in ("http","https") else None
        except ValueError:
            provider=None
        if provider:
            store.append({"qr_slug":c["slug"],"qr_name":c["name"],
                          "store":provider,"verified_qr_scans":counts.get(c["id"],0),
                          "confirmed_downloads":"Not connected"})
    return {"meta":{"source":"SQLite mode=ro","qr_id":qr_id or "All",
                    "verified_scans":total,
                    "note":"QR scans are not app downloads; city is not district. IDs are pseudonymous browser IDs."},
            "locations":geo,"device_types":systems,"devices_per_qr":devices,"store_qr_traffic":store}

def save_csv(filename,items):
    if not items:
        Path(filename).write_text("No records\n",encoding="utf-8-sig")
        return
    with open(filename,"w",newline="",encoding="utf-8-sig") as out:
        w=csv.writer(out)
        cols=list(items[0])
        w.writerow(cols)
        for row in items:
            w.writerow([safe_csv(row.get(c)) for c in cols])

def save_pdf(path,report):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
    styles=getSampleStyleSheet()
    story=[Paragraph("NextToppers QR - Read-only Insights",styles["Title"]),
           Paragraph(escape(str(report["meta"])),styles["Normal"]),Spacer(1,15)]
    for title,key in (("Countries / regions / cities","locations"),
                      ("Device OS / browser","device_types"),
                      ("Most active device IDs per QR","devices_per_qr"),
                      ("Store QR scans (NOT installs)","store_qr_traffic")):
        story.append(Paragraph(title,styles["Heading2"]))
        data=report[key][:25]
        if not data:
            story.append(Paragraph("No records",styles["Normal"]))
            continue
        fields=list(data[0])[:5]
        cells=[[Paragraph(escape(x),styles["BodyText"]) for x in fields]]
        for row in data:
            cells.append([Paragraph(escape(str(row.get(x,""))[:80]),styles["BodyText"]) for x in fields])
        t=Table(cells,colWidths=[100]*len(fields),repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
                               ("VALIGN",(0,0),(-1,-1),"TOP"),
                               ("BOTTOMPADDING",(0,0),(-1,-1),7)]))
        story.append(t);story.append(Spacer(1,12))
    SimpleDocTemplate(str(path)).build(story)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--database",required=True,help="Explicit absolute service/API timetable.db")
    p.add_argument("--output-dir",required=True)
    p.add_argument("--qr-id",default=None)
    p.add_argument("--max-devices",type=int,default=50000)
    args=p.parse_args()
    db=connect_readonly(args.database)
    try:
        result=summarize(db,args.qr_id,args.max_devices)
    finally:
        db.close()
    dest=Path(args.output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    for key in ("locations","device_types","devices_per_qr","store_qr_traffic"):
        save_csv(dest/(key+".csv"),result[key])
    save_pdf(dest/"qr_insights.pdf",result)
    (dest/"summary.json").write_text(json.dumps(result["meta"],indent=2),encoding="utf-8")
    print(json.dumps({"ok":True,"output":str(dest),"meta":result["meta"]},indent=2))

if __name__=="__main__":
    main()
