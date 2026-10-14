from __future__ import annotations

import asyncio
import base64
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import get_database

router = APIRouter(prefix="/api/v1/qr-scale", tags=["qr-scale"])
_SCHEMA_VERSION = "3"


def _encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        result = json.loads(decoded.decode("utf-8"))
        return result if isinstance(result, dict) else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


def _public_url(row: Any) -> str:
    short_url = str(row["short_url"] or "").strip() if "short_url" in row.keys() else ""
    if short_url:
        return short_url
    base = str(row["public_base_url"] or "").rstrip("/") if "public_base_url" in row.keys() else ""
    slug = str(row["slug"])
    return f"{base}/q/{slug}" if base else f"/q/{slug}"


def _safe_json(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


_SCALE_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS qr_scale_totals (
    qr_id TEXT PRIMARY KEY,
    verified_scans INTEGER NOT NULL DEFAULT 0,
    legacy_scans INTEGER NOT NULL DEFAULT 0,
    identified_scans INTEGER NOT NULL DEFAULT 0,
    anonymous_scans INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    unique_emails INTEGER NOT NULL DEFAULT 0,
    country_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_daily (
    day TEXT NOT NULL,
    qr_id TEXT NOT NULL,
    verified_scans INTEGER NOT NULL DEFAULT 0,
    identified_scans INTEGER NOT NULL DEFAULT 0,
    anonymous_scans INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(day, qr_id),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_dimensions (
    day TEXT NOT NULL,
    qr_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    value TEXT NOT NULL,
    scans INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(day, qr_id, dimension, value),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_visitors (
    qr_id TEXT NOT NULL,
    visitor_hash TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    scans INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(qr_id, visitor_hash),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_daily_visitors (
    day TEXT NOT NULL,
    qr_id TEXT NOT NULL,
    visitor_hash TEXT NOT NULL,
    PRIMARY KEY(day, qr_id, visitor_hash),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_emails (
    qr_id TEXT NOT NULL,
    email TEXT NOT NULL,
    PRIMARY KEY(qr_id, email),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS qr_scale_countries (
    qr_id TEXT NOT NULL,
    country TEXT NOT NULL,
    PRIMARY KEY(qr_id, country),
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_qr_scale_daily_day ON qr_scale_daily(day, qr_id);
CREATE INDEX IF NOT EXISTS idx_qr_scale_dimensions_lookup ON qr_scale_dimensions(dimension, day, qr_id, scans DESC);
CREATE INDEX IF NOT EXISTS idx_qr_scale_daily_visitors_day ON qr_scale_daily_visitors(day, qr_id, visitor_hash);
CREATE INDEX IF NOT EXISTS idx_qr_scale_visitors_qr ON qr_scale_visitors(qr_id, scans DESC);
CREATE INDEX IF NOT EXISTS idx_qr_codes_scale_recent ON qr_codes(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_qr_codes_scale_name ON qr_codes(name COLLATE NOCASE, id);
CREATE INDEX IF NOT EXISTS idx_qr_codes_scale_target ON qr_codes(target_url COLLATE NOCASE, id);
CREATE INDEX IF NOT EXISTS idx_qr_codes_scale_type_active ON qr_codes(qr_type, active, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_qr_scans_scale_human_time ON qr_scans(confirmed, device_type, scanned_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_qr_scans_scale_qr_human_time ON qr_scans(qr_id, confirmed, device_type, scanned_at DESC, id DESC);

DROP TRIGGER IF EXISTS trg_qr_scale_scan_insert;

DROP TRIGGER IF EXISTS trg_qr_scale_scan_delete;
CREATE TRIGGER trg_qr_scale_scan_delete AFTER DELETE ON qr_scans
WHEN OLD.id <= COALESCE(CAST((SELECT value FROM app_metadata WHERE key='qr_scale_last_scan_id') AS INTEGER),0)
BEGIN
    UPDATE qr_scale_totals SET
        verified_scans=MAX(0,verified_scans-CASE WHEN OLD.confirmed=1 AND OLD.device_type!='bot' THEN 1 ELSE 0 END),
        legacy_scans=MAX(0,legacy_scans-CASE WHEN OLD.confirmed=0 THEN 1 ELSE 0 END),
        identified_scans=MAX(0,identified_scans-CASE WHEN OLD.confirmed=1 AND OLD.device_type!='bot' AND trim(OLD.scanner_email)!='' THEN 1 ELSE 0 END),
        anonymous_scans=MAX(0,anonymous_scans-CASE WHEN OLD.confirmed=1 AND OLD.device_type!='bot' AND trim(OLD.scanner_email)='' THEN 1 ELSE 0 END),
        updated_at=OLD.scanned_at
    WHERE qr_id=OLD.qr_id;

    UPDATE qr_scale_daily SET
        verified_scans=MAX(0,verified_scans-1),
        identified_scans=MAX(0,identified_scans-CASE WHEN trim(OLD.scanner_email)!='' THEN 1 ELSE 0 END),
        anonymous_scans=MAX(0,anonymous_scans-CASE WHEN trim(OLD.scanner_email)='' THEN 1 ELSE 0 END)
    WHERE OLD.confirmed=1 AND OLD.device_type!='bot' AND day=date(OLD.scanned_at,'+5 hours','+30 minutes') AND qr_id=OLD.qr_id;
    DELETE FROM qr_scale_daily WHERE verified_scans<=0;

    UPDATE qr_scale_visitors SET scans=MAX(0,scans-1)
    WHERE OLD.confirmed=1 AND OLD.device_type!='bot' AND qr_id=OLD.qr_id AND visitor_hash=OLD.visitor_hash;
    DELETE FROM qr_scale_visitors WHERE scans<=0;

    DELETE FROM qr_scale_daily_visitors
    WHERE OLD.confirmed=1 AND OLD.device_type!='bot'
      AND day=date(OLD.scanned_at,'+5 hours','+30 minutes') AND qr_id=OLD.qr_id AND visitor_hash=OLD.visitor_hash
      AND NOT EXISTS (
        SELECT 1 FROM qr_scans s WHERE s.qr_id=OLD.qr_id AND s.visitor_hash=OLD.visitor_hash
          AND s.confirmed=1 AND s.device_type!='bot'
          AND date(s.scanned_at,'+5 hours','+30 minutes')=date(OLD.scanned_at,'+5 hours','+30 minutes')
      );

    DELETE FROM qr_scale_emails
    WHERE trim(OLD.scanner_email)!='' AND qr_id=OLD.qr_id AND email=lower(trim(OLD.scanner_email))
      AND NOT EXISTS (SELECT 1 FROM qr_scans s WHERE s.qr_id=OLD.qr_id AND lower(trim(s.scanner_email))=lower(trim(OLD.scanner_email)) AND s.confirmed=1 AND s.device_type!='bot');

    DELETE FROM qr_scale_countries
    WHERE OLD.country!='Unknown' AND qr_id=OLD.qr_id AND country=OLD.country
      AND NOT EXISTS (SELECT 1 FROM qr_scans s WHERE s.qr_id=OLD.qr_id AND s.country=OLD.country AND s.confirmed=1 AND s.device_type!='bot');

    UPDATE qr_scale_totals SET
      unique_visitors=(SELECT COUNT(*) FROM qr_scale_visitors v WHERE v.qr_id=OLD.qr_id),
      unique_emails=(SELECT COUNT(*) FROM qr_scale_emails e WHERE e.qr_id=OLD.qr_id),
      country_count=(SELECT COUNT(*) FROM qr_scale_countries c WHERE c.qr_id=OLD.qr_id)
    WHERE qr_id=OLD.qr_id;

    UPDATE qr_scale_dimensions SET scans=MAX(0,scans-1)
    WHERE OLD.confirmed=1 AND OLD.device_type!='bot'
      AND day=date(OLD.scanned_at,'+5 hours','+30 minutes') AND qr_id=OLD.qr_id
      AND ((dimension='country' AND value=COALESCE(NULLIF(OLD.country,''),'Unknown'))
        OR (dimension='device' AND value=COALESCE(NULLIF(OLD.device_type,''),'Other'))
        OR (dimension='browser' AND value=COALESCE(NULLIF(OLD.browser,''),'Other'))
        OR (dimension='os' AND value=COALESCE(NULLIF(OLD.operating_system,''),'Other'))
        OR (dimension='platform' AND value=COALESCE(NULLIF(OLD.platform,''),'Direct / QR'))
        OR (dimension='confidence' AND value=COALESCE(NULLIF(OLD.source_confidence,''),'unknown')));
    DELETE FROM qr_scale_dimensions WHERE scans<=0;
END;
"""


def ensure_qr_scale_schema() -> None:
    database = get_database()
    with database.connect() as connection:
        connection.executescript(_SCALE_SCHEMA)
        total_columns = {row[1] for row in connection.execute("PRAGMA table_info(qr_scale_totals)").fetchall()}
        for column in ("unique_visitors", "unique_emails", "country_count"):
            if column not in total_columns:
                connection.execute(f"ALTER TABLE qr_scale_totals ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
        marker = connection.execute(
            "SELECT value FROM app_metadata WHERE key='qr_scale_schema_version'"
        ).fetchone()
        if marker and str(marker[0]) == _SCHEMA_VERSION:
            return

        # New aggregate tables are derived only. Rebuild them from raw QR history once.
        for table in (
            "qr_scale_totals", "qr_scale_daily", "qr_scale_dimensions", "qr_scale_visitors",
            "qr_scale_daily_visitors", "qr_scale_emails", "qr_scale_countries",
        ):
            connection.execute(f"DELETE FROM {table}")

        connection.execute(
            """INSERT INTO qr_scale_totals(qr_id,verified_scans,legacy_scans,identified_scans,anonymous_scans,unique_visitors,unique_emails,country_count,updated_at)
               SELECT q.id,
                      COALESCE(SUM(CASE WHEN s.confirmed=1 AND s.device_type!='bot' THEN 1 ELSE 0 END),0),
                      COALESCE(SUM(CASE WHEN s.confirmed=0 THEN 1 ELSE 0 END),0),
                      COALESCE(SUM(CASE WHEN s.confirmed=1 AND s.device_type!='bot' AND trim(s.scanner_email)!='' THEN 1 ELSE 0 END),0),
                      COALESCE(SUM(CASE WHEN s.confirmed=1 AND s.device_type!='bot' AND trim(s.scanner_email)='' THEN 1 ELSE 0 END),0),
                      COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type!='bot' THEN s.visitor_hash END),
                      COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type!='bot' AND trim(s.scanner_email)!='' THEN lower(trim(s.scanner_email)) END),
                      COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type!='bot' AND s.country!='Unknown' AND trim(s.country)!='' THEN s.country END),
                      MAX(s.scanned_at)
               FROM qr_codes q LEFT JOIN qr_scans s ON s.qr_id=q.id GROUP BY q.id"""
        )
        connection.execute(
            """INSERT INTO qr_scale_daily(day,qr_id,verified_scans,identified_scans,anonymous_scans)
               SELECT date(scanned_at,'+5 hours','+30 minutes'),qr_id,COUNT(*),
                      SUM(CASE WHEN trim(scanner_email)!='' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN trim(scanner_email)='' THEN 1 ELSE 0 END)
               FROM qr_scans WHERE confirmed=1 AND device_type!='bot'
               GROUP BY date(scanned_at,'+5 hours','+30 minutes'),qr_id"""
        )
        connection.execute(
            """INSERT INTO qr_scale_visitors(qr_id,visitor_hash,first_seen,last_seen,scans)
               SELECT qr_id,visitor_hash,MIN(scanned_at),MAX(scanned_at),COUNT(*)
               FROM qr_scans WHERE confirmed=1 AND device_type!='bot' AND trim(visitor_hash)!=''
               GROUP BY qr_id,visitor_hash"""
        )
        connection.execute(
            """INSERT INTO qr_scale_daily_visitors(day,qr_id,visitor_hash)
               SELECT DISTINCT date(scanned_at,'+5 hours','+30 minutes'),qr_id,visitor_hash
               FROM qr_scans WHERE confirmed=1 AND device_type!='bot' AND trim(visitor_hash)!=''"""
        )
        connection.execute(
            """INSERT INTO qr_scale_emails(qr_id,email)
               SELECT DISTINCT qr_id,lower(trim(scanner_email)) FROM qr_scans
               WHERE confirmed=1 AND device_type!='bot' AND trim(scanner_email)!=''"""
        )
        connection.execute(
            """INSERT INTO qr_scale_countries(qr_id,country)
               SELECT DISTINCT qr_id,country FROM qr_scans
               WHERE confirmed=1 AND device_type!='bot' AND country!='Unknown' AND trim(country)!=''"""
        )
        for dimension, column, fallback in (
            ("country", "country", "Unknown"),
            ("device", "device_type", "Other"),
            ("browser", "browser", "Other"),
            ("os", "operating_system", "Other"),
            ("platform", "platform", "Direct / QR"),
            ("confidence", "source_confidence", "unknown"),
        ):
            connection.execute(
                f"""INSERT INTO qr_scale_dimensions(day,qr_id,dimension,value,scans)
                    SELECT date(scanned_at,'+5 hours','+30 minutes'),qr_id,?,COALESCE(NULLIF({column},''),?),COUNT(*)
                    FROM qr_scans WHERE confirmed=1 AND device_type!='bot'
                    GROUP BY date(scanned_at,'+5 hours','+30 minutes'),qr_id,COALESCE(NULLIF({column},''),?)""",
                (dimension, fallback, fallback),
            )
        max_scan_id = int(connection.execute("SELECT COALESCE(MAX(id),0) FROM qr_scans").fetchone()[0])
        connection.execute(
            "INSERT INTO app_metadata(key,value) VALUES('qr_scale_last_scan_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(max_scan_id),),
        )
        connection.execute(
            "INSERT INTO app_metadata(key,value) VALUES('qr_scale_schema_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_SCHEMA_VERSION,),
        )



def process_qr_scale_pending(batch_size: int = 5000) -> int:
    """Aggregate new raw scan rows in batches. The QR redirect path only writes raw scans."""
    database = get_database()
    with database.connect() as connection:
        marker = connection.execute("SELECT value FROM app_metadata WHERE key='qr_scale_last_scan_id'").fetchone()
        last_id = int(marker[0]) if marker and str(marker[0]).isdigit() else 0
        ids = connection.execute(
            "SELECT id FROM qr_scans WHERE id>? ORDER BY id LIMIT ?", (last_id, max(1, min(batch_size, 20000)))
        ).fetchall()
        if not ids:
            return 0
        batch_max = int(ids[-1][0])
        scope = "id>? AND id<=?"
        params = (last_id, batch_max)

        connection.execute(
            f"""INSERT INTO qr_scale_totals(qr_id,verified_scans,legacy_scans,identified_scans,anonymous_scans,unique_visitors,unique_emails,country_count,updated_at)
                SELECT qr_id,
                       SUM(CASE WHEN confirmed=1 AND device_type!='bot' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN confirmed=0 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN confirmed=1 AND device_type!='bot' AND trim(scanner_email)!='' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN confirmed=1 AND device_type!='bot' AND trim(scanner_email)='' THEN 1 ELSE 0 END),
                       0,0,0,
                       MAX(scanned_at)
                FROM qr_scans WHERE {scope} GROUP BY qr_id
                ON CONFLICT(qr_id) DO UPDATE SET
                  verified_scans=verified_scans+excluded.verified_scans,
                  legacy_scans=legacy_scans+excluded.legacy_scans,
                  identified_scans=identified_scans+excluded.identified_scans,
                  anonymous_scans=anonymous_scans+excluded.anonymous_scans,
                  updated_at=excluded.updated_at""", params
        )
        connection.execute(
            f"""INSERT INTO qr_scale_daily(day,qr_id,verified_scans,identified_scans,anonymous_scans)
                SELECT date(scanned_at,'+5 hours','+30 minutes'),qr_id,COUNT(*),
                       SUM(CASE WHEN trim(scanner_email)!='' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN trim(scanner_email)='' THEN 1 ELSE 0 END)
                FROM qr_scans WHERE {scope} AND confirmed=1 AND device_type!='bot'
                GROUP BY date(scanned_at,'+5 hours','+30 minutes'),qr_id
                ON CONFLICT(day,qr_id) DO UPDATE SET
                  verified_scans=verified_scans+excluded.verified_scans,
                  identified_scans=identified_scans+excluded.identified_scans,
                  anonymous_scans=anonymous_scans+excluded.anonymous_scans""", params
        )
        connection.execute(
            f"""INSERT INTO qr_scale_visitors(qr_id,visitor_hash,first_seen,last_seen,scans)
                SELECT qr_id,visitor_hash,MIN(scanned_at),MAX(scanned_at),COUNT(*)
                FROM qr_scans WHERE {scope} AND confirmed=1 AND device_type!='bot' AND trim(visitor_hash)!=''
                GROUP BY qr_id,visitor_hash
                ON CONFLICT(qr_id,visitor_hash) DO UPDATE SET
                  first_seen=MIN(first_seen,excluded.first_seen),last_seen=MAX(last_seen,excluded.last_seen),scans=scans+excluded.scans""", params
        )
        connection.execute(
            f"""INSERT OR IGNORE INTO qr_scale_daily_visitors(day,qr_id,visitor_hash)
                SELECT DISTINCT date(scanned_at,'+5 hours','+30 minutes'),qr_id,visitor_hash
                FROM qr_scans WHERE {scope} AND confirmed=1 AND device_type!='bot' AND trim(visitor_hash)!=''""", params
        )
        connection.execute(
            f"""INSERT OR IGNORE INTO qr_scale_emails(qr_id,email)
                SELECT DISTINCT qr_id,lower(trim(scanner_email)) FROM qr_scans
                WHERE {scope} AND confirmed=1 AND device_type!='bot' AND trim(scanner_email)!=''""", params
        )
        connection.execute(
            f"""INSERT OR IGNORE INTO qr_scale_countries(qr_id,country)
                SELECT DISTINCT qr_id,country FROM qr_scans
                WHERE {scope} AND confirmed=1 AND device_type!='bot' AND country!='Unknown' AND trim(country)!=''""", params
        )
        connection.execute(
            f"""UPDATE qr_scale_totals SET
                    unique_visitors=(SELECT COUNT(*) FROM qr_scale_visitors v WHERE v.qr_id=qr_scale_totals.qr_id),
                    unique_emails=(SELECT COUNT(*) FROM qr_scale_emails e WHERE e.qr_id=qr_scale_totals.qr_id),
                    country_count=(SELECT COUNT(*) FROM qr_scale_countries c WHERE c.qr_id=qr_scale_totals.qr_id)
                WHERE qr_id IN (SELECT DISTINCT qr_id FROM qr_scans WHERE {scope})""", params
        )
        for dimension, column, fallback in (
            ("country", "country", "Unknown"), ("device", "device_type", "Other"),
            ("browser", "browser", "Other"), ("os", "operating_system", "Other"),
            ("platform", "platform", "Direct / QR"), ("confidence", "source_confidence", "unknown"),
        ):
            connection.execute(
                f"""INSERT INTO qr_scale_dimensions(day,qr_id,dimension,value,scans)
                    SELECT date(scanned_at,'+5 hours','+30 minutes'),qr_id,?,COALESCE(NULLIF({column},''),?),COUNT(*)
                    FROM qr_scans WHERE {scope} AND confirmed=1 AND device_type!='bot'
                    GROUP BY date(scanned_at,'+5 hours','+30 minutes'),qr_id,COALESCE(NULLIF({column},''),?)
                    ON CONFLICT(day,qr_id,dimension,value) DO UPDATE SET scans=scans+excluded.scans""",
                (dimension, fallback, *params, fallback),
            )
        connection.execute(
            "INSERT INTO app_metadata(key,value) VALUES('qr_scale_last_scan_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(batch_max),),
        )
        return len(ids)


async def qr_scale_aggregation_loop() -> None:
    """Background aggregation keeps analytics work off the QR redirect request path."""
    await asyncio.sleep(2)
    while True:
        try:
            # Bound each cycle so analytics cannot monopolize the API process.
            for _ in range(4):
                processed = await asyncio.to_thread(process_qr_scale_pending, 5000)
                if processed < 5000:
                    break
        except Exception:
            pass
        await asyncio.sleep(2)


def _filters(q: str, active: str, qr_type: str, template_id: str) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if q.strip():
        needle = f"{q.strip()}%"
        clauses.append("(q.name LIKE ? COLLATE NOCASE OR q.slug LIKE ? COLLATE NOCASE OR q.target_url LIKE ? COLLATE NOCASE)")
        params.extend((needle, needle, needle))
    if active == "active":
        clauses.append("q.active=1")
    elif active == "inactive":
        clauses.append("q.active=0")
    if qr_type and qr_type != "all":
        clauses.append("q.qr_type=?")
        params.append(qr_type)
    if template_id:
        clauses.append("q.template_id=?")
        params.append(template_id)
    return clauses, params


@router.get("/health")
def qr_scale_health() -> dict[str, Any]:
    ensure_qr_scale_schema()
    database = get_database()
    with database.connect() as connection:
        values = connection.execute(
            """SELECT
                 (SELECT COUNT(*) FROM qr_codes) AS qr_codes,
                 (SELECT COUNT(*) FROM qr_scans) AS raw_scans,
                 (SELECT COALESCE(SUM(verified_scans),0) FROM qr_scale_totals) AS verified_scans,
                 (SELECT COUNT(*) FROM qr_scale_visitors) AS unique_devices,
                 (SELECT value FROM app_metadata WHERE key='qr_scale_schema_version') AS schema_version"""
        ).fetchone()
    return dict(values)


@router.get("/codes")
def qr_scale_codes(
    limit: int = Query(25, ge=10, le=100),
    cursor: str | None = None,
    q: str = "",
    active: Literal["all", "active", "inactive"] = "all",
    qr_type: str = "all",
    template_id: str = "",
    sort: Literal["recent", "oldest", "name", "scans"] = "recent",
) -> dict[str, Any]:
    ensure_qr_scale_schema()
    database = get_database()
    decoded = _decode_cursor(cursor)
    clauses, params = _filters(q, active, qr_type, template_id)

    order = "q.created_at DESC,q.id DESC"
    if sort == "oldest":
        order = "q.created_at ASC,q.id ASC"
    elif sort == "name":
        order = "lower(q.name) ASC,q.id ASC"
    elif sort == "scans":
        order = "COALESCE(m.verified_scans,0) DESC,q.id ASC"

    if decoded:
        if decoded.get("sort") != sort:
            raise HTTPException(status_code=400, detail="Cursor does not match sort order")
        if sort == "recent":
            clauses.append("(q.created_at < ? OR (q.created_at=? AND q.id<?))")
            params.extend((decoded.get("created"), decoded.get("created"), decoded.get("id")))
        elif sort == "oldest":
            clauses.append("(q.created_at > ? OR (q.created_at=? AND q.id>?))")
            params.extend((decoded.get("created"), decoded.get("created"), decoded.get("id")))
        elif sort == "name":
            clauses.append("(lower(q.name) > ? OR (lower(q.name)=? AND q.id>?))")
            params.extend((decoded.get("name"), decoded.get("name"), decoded.get("id")))
        else:
            clauses.append("(COALESCE(m.verified_scans,0) < ? OR (COALESCE(m.verified_scans,0)=? AND q.id>?))")
            params.extend((decoded.get("scans"), decoded.get("scans"), decoded.get("id")))

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    base_clauses, base_params = _filters(q, active, qr_type, template_id)
    base_where = "WHERE " + " AND ".join(base_clauses) if base_clauses else ""

    with database.connect() as connection:
        total = int(connection.execute(f"SELECT COUNT(*) FROM qr_codes q {base_where}", tuple(base_params)).fetchone()[0])
        rows = connection.execute(
            f"""SELECT q.id,q.name,q.slug,q.qr_type,q.tracking_mode,q.identity_mode,q.target_url,q.payload_json,
                       q.public_base_url,q.short_url,q.template_id,t.name AS template_name,q.active,q.created_at,q.updated_at,
                       COALESCE(m.verified_scans,0) AS total_scans,
                       COALESCE(m.legacy_scans,0) AS legacy_scans,
                       COALESCE(m.unique_visitors,0) AS unique_visitors,
                       COALESCE(m.unique_emails,0) AS unique_emails,
                       COALESCE(m.country_count,0) AS country_count
                FROM qr_codes q
                LEFT JOIN qr_templates t ON t.id=q.template_id
                LEFT JOIN qr_scale_totals m ON m.qr_id=q.id
                {where}
                ORDER BY {order}
                LIMIT ?""",
            tuple(params + [limit + 1]),
        ).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = _safe_json(row["payload_json"])
        source_url = str(payload.get("url") or row["target_url"] or "")
        items.append({
            "id": str(row["id"]), "name": str(row["name"]), "slug": str(row["slug"]),
            "qr_type": str(row["qr_type"]), "tracking_mode": str(row["tracking_mode"]),
            "identity_mode": str(row["identity_mode"]), "target_url": str(row["target_url"] or ""),
            "source_url": source_url, "public_url": _public_url(row), "active": bool(row["active"]),
            "created_at": str(row["created_at"]), "updated_at": str(row["updated_at"]),
            "template_id": row["template_id"], "template_name": row["template_name"],
            "total_scans": int(row["total_scans"] or 0), "legacy_scans": int(row["legacy_scans"] or 0),
            "unique_visitors": int(row["unique_visitors"] or 0), "unique_emails": int(row["unique_emails"] or 0),
            "country_count": int(row["country_count"] or 0),
        })

    next_cursor = None
    if has_more and rows:
        row = rows[-1]
        if sort in {"recent", "oldest"}:
            next_cursor = _encode_cursor({"sort": sort, "created": str(row["created_at"]), "id": str(row["id"])})
        elif sort == "name":
            next_cursor = _encode_cursor({"sort": sort, "name": str(row["name"]).casefold(), "id": str(row["id"])})
        else:
            next_cursor = _encode_cursor({"sort": sort, "scans": int(row["total_scans"] or 0), "id": str(row["id"])})

    return {"items": items, "total": total, "limit": limit, "next_cursor": next_cursor, "has_more": has_more}


def _period_start(period: str) -> str | None:
    if period == "all":
        return None
    days = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}.get(period, 30)
    india_today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    return (india_today - timedelta(days=days - 1)).isoformat()


@router.get("/analytics")
def qr_scale_analytics(
    period: Literal["7d", "30d", "90d", "365d", "all"] = "30d",
    qr_id: str = "",
) -> dict[str, Any]:
    ensure_qr_scale_schema()
    database = get_database()
    start = _period_start(period)
    day_clause = ""
    day_params: list[Any] = []
    if start:
        day_clause = "day>=?"
        day_params.append(start)
    qr_clause = "qr_id=?" if qr_id else ""
    qr_params: list[Any] = [qr_id] if qr_id else []
    clauses = [value for value in (day_clause, qr_clause) if value]
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params = day_params + qr_params

    with database.connect() as connection:
        totals = connection.execute(
            f"""SELECT COALESCE(SUM(verified_scans),0) AS verified_scans,
                       COALESCE(SUM(identified_scans),0) AS identified_scans,
                       COALESCE(SUM(anonymous_scans),0) AS anonymous_scans
                FROM qr_scale_daily {where}""",
            tuple(params),
        ).fetchone()

        if start:
            unique_where = "WHERE day>=?" + (" AND qr_id=?" if qr_id else "")
            unique_params = [start] + ([qr_id] if qr_id else [])
            unique_devices = int(connection.execute(
                f"SELECT COUNT(DISTINCT visitor_hash) FROM qr_scale_daily_visitors {unique_where}",
                tuple(unique_params),
            ).fetchone()[0])
        elif qr_id:
            unique_devices = int(connection.execute("SELECT COUNT(*) FROM qr_scale_visitors WHERE qr_id=?", (qr_id,)).fetchone()[0])
        else:
            unique_devices = int(connection.execute("SELECT COUNT(DISTINCT visitor_hash) FROM qr_scale_visitors").fetchone()[0])

        email_sql = "SELECT COUNT(*) FROM qr_scale_emails" + (" WHERE qr_id=?" if qr_id else "")
        unique_emails = int(connection.execute(email_sql, (qr_id,) if qr_id else ()).fetchone()[0])

        active_qr = int(connection.execute("SELECT COUNT(*) FROM qr_codes WHERE active=1" + (" AND id=?" if qr_id else ""), (qr_id,) if qr_id else ()).fetchone()[0])
        total_qr = int(connection.execute("SELECT COUNT(*) FROM qr_codes" + (" WHERE id=?" if qr_id else ""), (qr_id,) if qr_id else ()).fetchone()[0])

        trend_rows = connection.execute(
            f"SELECT day,SUM(verified_scans) AS scans FROM qr_scale_daily {where} GROUP BY day ORDER BY day",
            tuple(params),
        ).fetchall()

        dimension_result: dict[str, dict[str, int]] = {}
        for dimension in ("country", "device", "browser", "os", "platform", "confidence"):
            dim_clauses = ["dimension=?"] + clauses
            dim_where = "WHERE " + " AND ".join(dim_clauses)
            rows = connection.execute(
                f"""SELECT value,SUM(scans) AS scans FROM qr_scale_dimensions {dim_where}
                    GROUP BY value ORDER BY scans DESC LIMIT 12""",
                tuple([dimension] + params),
            ).fetchall()
            dimension_result[dimension] = {str(row["value"]): int(row["scans"] or 0) for row in rows}

        top_qr_clauses = clauses.copy()
        top_qr_where = "WHERE " + " AND ".join(top_qr_clauses) if top_qr_clauses else ""
        top_rows = connection.execute(
            f"""SELECT d.qr_id,q.name,q.slug,q.target_url,SUM(d.verified_scans) AS scans
                FROM qr_scale_daily d JOIN qr_codes q ON q.id=d.qr_id
                {top_qr_where}
                GROUP BY d.qr_id,q.name,q.slug,q.target_url
                ORDER BY scans DESC LIMIT 12""",
            tuple(params),
        ).fetchall()

    return {
        "period": period,
        "qr_id": qr_id or None,
        "total_qr_codes": total_qr,
        "active_qr_codes": active_qr,
        "verified_scans": int(totals["verified_scans"] or 0),
        "unique_devices": unique_devices,
        "unique_emails": unique_emails,
        "identified_scans": int(totals["identified_scans"] or 0),
        "anonymous_scans": int(totals["anonymous_scans"] or 0),
        "trend": [{"day": str(row["day"]), "scans": int(row["scans"] or 0)} for row in trend_rows],
        "countries": dimension_result["country"],
        "devices": dimension_result["device"],
        "browsers": dimension_result["browser"],
        "operating_systems": dimension_result["os"],
        "platforms": dimension_result["platform"],
        "confidence": dimension_result["confidence"],
        "top_qr_codes": [
            {"id": str(row["qr_id"]), "name": str(row["name"]), "slug": str(row["slug"]), "target_url": str(row["target_url"] or ""), "scans": int(row["scans"] or 0)}
            for row in top_rows
        ],
    }


@router.get("/recent-scans")
def qr_scale_recent_scans(
    limit: int = Query(25, ge=10, le=100),
    cursor: int | None = Query(None, ge=1),
    qr_id: str = "",
) -> dict[str, Any]:
    ensure_qr_scale_schema()
    database = get_database()
    clauses = ["s.confirmed=1", "s.device_type!='bot'"]
    params: list[Any] = []
    if qr_id:
        clauses.append("s.qr_id=?")
        params.append(qr_id)
    if cursor:
        clauses.append("s.id<?")
        params.append(cursor)
    where = " AND ".join(clauses)
    with database.connect() as connection:
        rows = connection.execute(
            f"""SELECT s.id,s.qr_id,q.name AS qr_name,s.scanned_at,s.country,s.device_type,s.browser,
                       s.operating_system,s.platform,s.source_confidence,s.scanner_email,s.visitor_hash
                FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id
                WHERE {where} ORDER BY s.id DESC LIMIT ?""",
            tuple(params + [limit + 1]),
        ).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [
            {
                "id": int(row["id"]), "qr_id": str(row["qr_id"]), "qr_name": str(row["qr_name"]),
                "scanned_at": str(row["scanned_at"]), "country": str(row["country"]),
                "device_type": str(row["device_type"]), "browser": str(row["browser"]),
                "operating_system": str(row["operating_system"]), "platform": str(row["platform"]),
                "source_confidence": str(row["source_confidence"]), "scanner_email": str(row["scanner_email"] or ""),
                "device_id": f"Device {str(row['visitor_hash'])[:8].upper()}",
            }
            for row in rows
        ],
        "next_cursor": int(rows[-1]["id"]) if has_more and rows else None,
        "has_more": has_more,
    }
