from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Sequence

from .timezones import INDIA_TIMEZONE
from .utils import normalize_search_text

from .models import (
    CellSnapshot,
    ChangeRecord,
    ContentItem,
    NotificationDelivery,
    NotificationRule,
    QrAnalyticsSummary,
    QrCodeRecord,
    QrDeviceSummary,
    QrDesignSettings,
    QrScanExperience,
    QrScanRecord,
    QrTemplateRecord,
    SheetSource,
    TestRecord,
    TimetableEntry,
    WorkbookProfile,
)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    spreadsheet_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_sync_at TEXT,
    last_sync_status TEXT NOT NULL DEFAULT 'never',
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS cells (
    stable_key TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    coordinate TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    column_number INTEGER NOT NULL,
    value TEXT NOT NULL,
    formula TEXT,
    hyperlink TEXT,
    style_key TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cells_source_sheet ON cells(source_id, sheet_name);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    payload TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timetable_source ON timetable_entries(source_id);
CREATE INDEX IF NOT EXISTS idx_timetable_fingerprint ON timetable_entries(fingerprint);
CREATE INDEX IF NOT EXISTS idx_timetable_class_date ON timetable_entries(json_extract(payload,'$.class_date'));
CREATE INDEX IF NOT EXISTS idx_timetable_date_time ON timetable_entries(json_extract(payload,'$.class_date'), json_extract(payload,'$.start_time'));

CREATE TABLE IF NOT EXISTS content_items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    payload TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_id);
CREATE INDEX IF NOT EXISTS idx_content_fingerprint ON content_items(fingerprint);

CREATE TABLE IF NOT EXISTS content_search_index (
    content_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_content_search_source ON content_search_index(source_id);

CREATE TABLE IF NOT EXISTS content_search_terms (
    content_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    token TEXT NOT NULL,
    PRIMARY KEY(content_id, token),
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_content_search_token ON content_search_terms(token);
CREATE INDEX IF NOT EXISTS idx_content_terms_source ON content_search_terms(source_id);


CREATE TABLE IF NOT EXISTS test_records (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    payload TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_test_records_source ON test_records(source_id);
CREATE INDEX IF NOT EXISTS idx_test_records_sheet ON test_records(source_id, sheet_name);
CREATE INDEX IF NOT EXISTS idx_test_records_first_seen ON test_records(first_seen_at DESC);

CREATE TABLE IF NOT EXISTS changes (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    coordinate TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL,
    field_name TEXT,
    row_label TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_changes_detected ON changes(detected_at DESC);

CREATE TABLE IF NOT EXISTS notification_rules (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    error TEXT,
    attempted_at TEXT NOT NULL,
    scheduled_for TEXT,
    is_test INTEGER NOT NULL DEFAULT 0,
    dedupe_key TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_attempted ON notification_deliveries(attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_rule ON notification_deliveries(rule_id, attempted_at DESC);

CREATE TABLE IF NOT EXISTS workbook_profiles (
    source_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS qr_codes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    qr_type TEXT NOT NULL DEFAULT 'url',
    tracking_mode TEXT NOT NULL DEFAULT 'tracked',
    identity_mode TEXT NOT NULL DEFAULT 'anonymous',
    target_url TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    public_base_url TEXT,
    short_url TEXT,
    design_json TEXT NOT NULL DEFAULT '{}',
    experience_json TEXT NOT NULL DEFAULT '{}',
    template_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_qr_codes_slug ON qr_codes(slug);
CREATE INDEX IF NOT EXISTS idx_qr_codes_active ON qr_codes(active, created_at DESC);

CREATE TABLE IF NOT EXISTS qr_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    tracking_mode TEXT NOT NULL DEFAULT 'tracked',
    identity_mode TEXT NOT NULL DEFAULT 'anonymous',
    design_json TEXT NOT NULL DEFAULT '{}',
    experience_json TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_qr_templates_default ON qr_templates(is_default, updated_at DESC);

CREATE TABLE IF NOT EXISTS qr_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qr_id TEXT NOT NULL,
    scanned_at TEXT NOT NULL,
    visitor_hash TEXT NOT NULL,
    event_hash TEXT,
    confirmed INTEGER NOT NULL DEFAULT 0,
    country TEXT NOT NULL DEFAULT 'Unknown',
    device_type TEXT NOT NULL DEFAULT 'Other',
    browser TEXT NOT NULL DEFAULT 'Other',
    operating_system TEXT NOT NULL DEFAULT 'Other',
    platform TEXT NOT NULL DEFAULT 'Direct / QR',
    source_confidence TEXT NOT NULL DEFAULT 'unknown',
    referrer_host TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT '',
    scanner_email TEXT NOT NULL DEFAULT '',
    device_model TEXT NOT NULL DEFAULT '',
    client_platform TEXT NOT NULL DEFAULT '',
    telemetry_json TEXT NOT NULL DEFAULT '{}',
    screen_width INTEGER,
    screen_height INTEGER,
    FOREIGN KEY(qr_id) REFERENCES qr_codes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_qr_scans_qr_time ON qr_scans(qr_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_qr_scans_time ON qr_scans(scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_qr_scans_country ON qr_scans(country);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    live_data INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    warning_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);
"""



def _content_search_document(item: ContentItem) -> tuple[str, str, list[str]]:
    fields = [item.title, item.url, item.stream, item.class_name, item.batch, item.subject,
              item.topic, item.teacher, item.sheet_name, item.workbook_name, item.search_text,
              item.status, item.test_number, item.test_date, item.result_dashboard,
              item.video_solution_update, item.questions, item.duration, item.marks, item.remarks,
              item.content_type.value]
    raw = " ".join(str(value) for value in fields if value)
    normalized = normalize_search_text(raw)
    tokens = sorted({token for token in normalized.split() if len(token) >= 2})
    return raw.casefold(), normalized, tokens



def _qr_telemetry_object(value: object) -> dict[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _qr_telemetry_text(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    return str(value)[:160] if value not in (None, "") else ""


def _qr_telemetry_number(data: dict[str, object], key: str) -> float | None:
    value = data.get(key)
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _qr_telemetry_bool(data: dict[str, object], key: str) -> bool | None:
    value = data.get(key)
    return value if isinstance(value, bool) else None


def _qr_languages(data: dict[str, object]) -> str:
    value = data.get("languages")
    if isinstance(value, list):
        return ", ".join(str(item)[:30] for item in value[:12] if str(item).strip())
    return ""


def _qr_input_capability(data: dict[str, object]) -> str:
    parts: list[str] = []
    pointer = _qr_telemetry_text(data, "primary_pointer")
    if pointer:
        parts.append(f"{pointer} pointer")
    touch = _qr_telemetry_number(data, "max_touch_points")
    if touch is not None:
        parts.append(f"{int(touch)} touch")
    hover = _qr_telemetry_bool(data, "hover_capable")
    if hover is not None:
        parts.append("hover" if hover else "no hover")
    return " · ".join(parts)


def _qr_form_factors(data: dict[str, object]) -> str:
    value = data.get("form_factors")
    if isinstance(value, list):
        return ", ".join(str(item)[:30] for item in value[:8] if str(item).strip())
    return ""


def _qr_network_label(data: dict[str, object]) -> str:
    effective = _qr_telemetry_text(data, "effective_connection_type")
    connection = _qr_telemetry_text(data, "connection_type")
    if connection and effective and connection.casefold() != effective.casefold():
        return f"{connection} · {effective} effective"
    return effective or connection


def _qr_network_quality(data: dict[str, object]) -> str:
    parts: list[str] = []
    downlink = _qr_telemetry_number(data, "downlink_mbps")
    rtt = _qr_telemetry_number(data, "rtt_ms")
    if downlink is not None:
        parts.append(f"{downlink:g} Mbps")
    if rtt is not None:
        parts.append(f"{int(rtt)} ms RTT")
    if data.get("save_data") is True:
        parts.append("Save-Data")
    return " · ".join(parts)


def _qr_viewport(data: dict[str, object]) -> str:
    width = _qr_telemetry_number(data, "viewport_width")
    height = _qr_telemetry_number(data, "viewport_height")
    if width and height:
        return f"{int(width)} x {int(height)}"
    return ""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA cache_size=-32768")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            change_columns = {row[1] for row in connection.execute("PRAGMA table_info(changes)").fetchall()}
            qr_columns = {row[1] for row in connection.execute("PRAGMA table_info(qr_codes)").fetchall()}
            if "short_url" not in qr_columns:
                connection.execute("ALTER TABLE qr_codes ADD COLUMN short_url TEXT")
            if "design_json" not in qr_columns:
                connection.execute("ALTER TABLE qr_codes ADD COLUMN design_json TEXT NOT NULL DEFAULT '{}'")
            if "experience_json" not in qr_columns:
                connection.execute("ALTER TABLE qr_codes ADD COLUMN experience_json TEXT NOT NULL DEFAULT '{}'")
            qr_code_migrations = {
                "qr_type": "TEXT NOT NULL DEFAULT 'url'",
                "template_id": "TEXT",
                "tracking_mode": "TEXT NOT NULL DEFAULT 'tracked'",
                "identity_mode": "TEXT NOT NULL DEFAULT 'anonymous'",
                "payload_json": "TEXT NOT NULL DEFAULT '{}'",
            }
            for column, definition in qr_code_migrations.items():
                if column not in qr_columns:
                    connection.execute(f"ALTER TABLE qr_codes ADD COLUMN {column} {definition}")
            qr_scan_columns = {row[1] for row in connection.execute("PRAGMA table_info(qr_scans)").fetchall()}
            qr_scan_migrations = {
                "event_hash": "TEXT",
                "confirmed": "INTEGER NOT NULL DEFAULT 0",
                "operating_system": "TEXT NOT NULL DEFAULT 'Other'",
                "platform": "TEXT NOT NULL DEFAULT 'Direct / QR'",
                "source_confidence": "TEXT NOT NULL DEFAULT 'unknown'",
                "referrer_host": "TEXT NOT NULL DEFAULT ''",
                "language": "TEXT NOT NULL DEFAULT ''",
                "timezone": "TEXT NOT NULL DEFAULT ''",
                "scanner_email": "TEXT NOT NULL DEFAULT ''",
                "device_model": "TEXT NOT NULL DEFAULT ''",
                "client_platform": "TEXT NOT NULL DEFAULT ''",
                "telemetry_json": "TEXT NOT NULL DEFAULT '{}'",
                "screen_width": "INTEGER",
                "screen_height": "INTEGER",
            }
            for column, definition in qr_scan_migrations.items():
                if column not in qr_scan_columns:
                    connection.execute(f"ALTER TABLE qr_scans ADD COLUMN {column} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_scans_platform ON qr_scans(platform, scanned_at DESC)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_scans_confirmed ON qr_scans(confirmed, scanned_at DESC)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_qr_scans_event ON qr_scans(event_hash) WHERE event_hash IS NOT NULL")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_scans_visitor ON qr_scans(visitor_hash, scanned_at DESC)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_scans_email ON qr_scans(scanner_email, scanned_at DESC)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_codes_template ON qr_codes(template_id, created_at DESC)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qr_templates_default ON qr_templates(is_default, updated_at DESC)")
            if "field_name" not in change_columns:
                connection.execute("ALTER TABLE changes ADD COLUMN field_name TEXT")
            if "row_label" not in change_columns:
                connection.execute("ALTER TABLE changes ADD COLUMN row_label TEXT")
            current = connection.execute(
                "SELECT value FROM app_metadata WHERE key='data_engine_version'"
            ).fetchone()
            if current is None or current[0] != "4":
                # v0.3.x missed some linked content and overwrote earlier Nirmaan
                # timetable/planner variants. Keep connections and notification
                # configuration, but rebuild all derived data with engine v4.
                connection.execute("DELETE FROM cells")
                connection.execute("DELETE FROM timetable_entries")
                connection.execute("DELETE FROM content_items")
                connection.execute("DELETE FROM changes")
                connection.execute("DELETE FROM workbook_profiles")
                connection.execute(
                    "UPDATE sources SET last_sync_at=NULL,last_sync_status='never',last_error=NULL"
                )
                connection.execute(
                    "INSERT INTO app_metadata(key,value) VALUES('data_engine_version','4') "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
                )

            indexed_count = connection.execute("SELECT COUNT(*) FROM content_search_index").fetchone()[0]
            content_count = connection.execute("SELECT COUNT(*) FROM content_items").fetchone()[0]
            if indexed_count != content_count:
                connection.execute("DELETE FROM content_search_terms")
                connection.execute("DELETE FROM content_search_index")
                for row in connection.execute("SELECT payload FROM content_items").fetchall():
                    item = ContentItem.model_validate_json(row["payload"])
                    raw, normalized, tokens = _content_search_document(item)
                    connection.execute(
                        "INSERT OR REPLACE INTO content_search_index(content_id,source_id,raw_text,normalized_text) VALUES(?,?,?,?)",
                        (item.id, item.source_id, raw, normalized),
                    )
                    connection.executemany(
                        "INSERT OR IGNORE INTO content_search_terms(content_id,source_id,token) VALUES(?,?,?)",
                        [(item.id, item.source_id, token) for token in tokens],
                    )

    def reset_interrupted_syncs(self) -> None:
        """Recover statuses left behind when Windows stopped during a check."""
        with self.connect() as connection:
            connection.execute(
                """UPDATE sources
                SET last_sync_status='interrupted',
                    last_error='The previous Google Sheet check stopped when the app restarted. Old local data is still available and the source will be checked again.'
                WHERE last_sync_status IN ('queued','downloading','analyzing')"""
            )

    def upsert_source(self, source: SheetSource) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sources(id,name,url,spreadsheet_id,enabled,created_at,last_sync_at,last_sync_status,last_error)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    url=excluded.url,
                    spreadsheet_id=excluded.spreadsheet_id,
                    enabled=excluded.enabled,
                    last_sync_at=excluded.last_sync_at,
                    last_sync_status=excluded.last_sync_status,
                    last_error=excluded.last_error
                """,
                (
                    source.id,
                    source.name,
                    source.url,
                    source.spreadsheet_id,
                    int(source.enabled),
                    source.created_at.isoformat(),
                    source.last_sync_at.isoformat() if source.last_sync_at else None,
                    source.last_sync_status,
                    source.last_error,
                ),
            )

    def list_sources(self) -> list[SheetSource]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM sources ORDER BY created_at").fetchall()
        return [self._row_to_source(row) for row in rows]

    def get_source(self, source_id: str) -> SheetSource | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        return self._row_to_source(row) if row else None

    def delete_source(self, source_id: str) -> bool:
        """Remove only the local connection and all locally indexed data.

        The Google Sheet itself is never edited or deleted.
        """
        with self.connect() as connection:
            for row in connection.execute("SELECT id,payload FROM notification_rules").fetchall():
                rule = NotificationRule.model_validate_json(row["payload"])
                if source_id in rule.source_ids:
                    updated = rule.model_copy(update={
                        "source_ids": [value for value in rule.source_ids if value != source_id]
                    })
                    connection.execute(
                        "UPDATE notification_rules SET payload=? WHERE id=?",
                        (updated.model_dump_json(), rule.id),
                    )
            cursor = connection.execute("DELETE FROM sources WHERE id=?", (source_id,))
            connection.execute("DELETE FROM app_metadata WHERE key=?", (f"test_baseline:{source_id}",))
            return cursor.rowcount > 0

    def source_test_count(self, source_id: str) -> int:
        with self.connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM test_records WHERE source_id=?", (source_id,)
            ).fetchone()[0])

    def test_sheet_counts(self, source_id: str | None = None) -> dict[str, int]:
        """Return Test Monitor tab totals with one small SQL aggregation.

        This avoids loading and validating every TestRecord just to render the tab bar.
        """
        sql = "SELECT sheet_name, COUNT(*) AS total FROM test_records"
        params: list[object] = []
        if source_id:
            sql += " WHERE source_id=?"
            params.append(source_id)
        sql += " GROUP BY sheet_name ORDER BY total DESC, sheet_name COLLATE NOCASE"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return {str(row["sheet_name"]): int(row["total"]) for row in rows}

    def update_source_sync_status(
        self,
        source_id: str,
        status: str,
        error: str | None = None,
        synced_at: datetime | None = None,
    ) -> None:
        with self.connect() as connection:
            if synced_at is None:
                connection.execute(
                    "UPDATE sources SET last_sync_status=?, last_error=? WHERE id=?",
                    (status, error, source_id),
                )
            else:
                connection.execute(
                    "UPDATE sources SET last_sync_at=?, last_sync_status=?, last_error=? WHERE id=?",
                    (synced_at.isoformat(), status, error, source_id),
                )

    def get_cells(self, source_id: str) -> list[CellSnapshot]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM cells WHERE source_id=?", (source_id,)
            ).fetchall()
        return [
            CellSnapshot(
                source_id=row["source_id"],
                workbook_name=row["workbook_name"],
                sheet_name=row["sheet_name"],
                coordinate=row["coordinate"],
                row=row["row_number"],
                column=row["column_number"],
                value=row["value"],
                formula=row["formula"],
                hyperlink=row["hyperlink"],
                style_key=row["style_key"],
            )
            for row in rows
        ]

    def replace_cells(self, source_id: str, cells: Sequence[CellSnapshot]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM cells WHERE source_id=?", (source_id,))
            connection.executemany(
                """
                INSERT INTO cells(stable_key,source_id,workbook_name,sheet_name,coordinate,row_number,column_number,value,formula,hyperlink,style_key)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        cell.stable_key,
                        cell.source_id,
                        cell.workbook_name,
                        cell.sheet_name,
                        cell.coordinate,
                        cell.row,
                        cell.column,
                        cell.value,
                        cell.formula,
                        cell.hyperlink,
                        cell.style_key,
                    )
                    for cell in cells
                ],
            )

    def replace_timetable(self, source_id: str, entries: Sequence[TimetableEntry]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM timetable_entries WHERE source_id=?", (source_id,))
            connection.executemany(
                "INSERT INTO timetable_entries(id,source_id,workbook_name,sheet_name,source_row,payload,fingerprint) VALUES(?,?,?,?,?,?,?)",
                [
                    (
                        item.id,
                        item.source_id,
                        item.workbook_name,
                        item.sheet_name,
                        item.source_row,
                        item.model_dump_json(),
                        item.fingerprint,
                    )
                    for item in entries
                ],
            )

    def replace_content(self, source_id: str, items: Sequence[ContentItem]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM content_search_terms WHERE source_id=?", (source_id,))
            connection.execute("DELETE FROM content_search_index WHERE source_id=?", (source_id,))
            connection.execute("DELETE FROM content_items WHERE source_id=?", (source_id,))
            connection.executemany(
                "INSERT INTO content_items(id,source_id,workbook_name,sheet_name,source_row,payload,fingerprint) VALUES(?,?,?,?,?,?,?)",
                [(item.id, item.source_id, item.workbook_name, item.sheet_name, item.source_row,
                  item.model_dump_json(), item.fingerprint) for item in items],
            )
            for item in items:
                raw, normalized, tokens = _content_search_document(item)
                connection.execute(
                    "INSERT INTO content_search_index(content_id,source_id,raw_text,normalized_text) VALUES(?,?,?,?)",
                    (item.id, item.source_id, raw, normalized),
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO content_search_terms(content_id,source_id,token) VALUES(?,?,?)",
                    [(item.id, item.source_id, token) for token in tokens],
                )

    def upsert_workbook_profile(self, profile: WorkbookProfile) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO workbook_profiles(source_id,payload,analyzed_at) VALUES(?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    payload=excluded.payload,
                    analyzed_at=excluded.analyzed_at
                """,
                (profile.source_id, profile.model_dump_json(), profile.analyzed_at.isoformat()),
            )

    def get_workbook_profile(self, source_id: str) -> WorkbookProfile | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM workbook_profiles WHERE source_id=?", (source_id,)
            ).fetchone()
        return WorkbookProfile.model_validate_json(row["payload"]) if row else None

    def source_record_counts(self, source_id: str) -> tuple[int, int]:
        with self.connect() as connection:
            timetable_count = connection.execute(
                "SELECT COUNT(*) FROM timetable_entries WHERE source_id=?", (source_id,)
            ).fetchone()[0]
            content_count = connection.execute(
                "SELECT COUNT(*) FROM content_items WHERE source_id=?", (source_id,)
            ).fetchone()[0]
        return int(timetable_count), int(content_count)

    def content_counts_by_tab(self, source_id: str) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT sheet_name,COUNT(*) AS item_count FROM content_items WHERE source_id=? GROUP BY sheet_name ORDER BY sheet_name",
                (source_id,),
            ).fetchall()
        return {str(row["sheet_name"]): int(row["item_count"]) for row in rows}

    def insert_changes(self, changes: Sequence[ChangeRecord]) -> None:
        if not changes:
            return
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO changes(id,source_id,workbook_name,sheet_name,coordinate,change_type,old_value,new_value,detected_at,field_name,row_label)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        item.id,
                        item.source_id,
                        item.workbook_name,
                        item.sheet_name,
                        item.coordinate,
                        item.change_type.value,
                        item.old_value,
                        item.new_value,
                        item.detected_at.isoformat(),
                        item.field_name,
                        item.row_label,
                    )
                    for item in changes
                ],
            )

    def list_timetable(self) -> list[TimetableEntry]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM timetable_entries").fetchall()
        items = [TimetableEntry.model_validate_json(row["payload"]) for row in rows]
        return sorted(
            items,
            key=lambda item: (
                item.class_date or datetime.max.date(),
                item.start_time or datetime.max.time(),
                item.stream or "",
                item.class_name or "",
                item.subject or "",
            ),
        )

    def list_timetable_page(
        self,
        *,
        page: int,
        page_size: int,
        class_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        stream: str | None = None,
        class_name: str | None = None,
        subject: str | None = None,
        latest: bool = False,
        upcoming: bool = False,
    ) -> tuple[list[TimetableEntry], int]:
        """Filter and paginate timetable rows in SQLite instead of loading the entire table."""
        clauses: list[str] = []
        params: list[object] = []
        resolved_date = class_date
        with self.connect() as connection:
            if resolved_date is None and upcoming:
                today = datetime.now(INDIA_TIMEZONE).date().isoformat()
                row = connection.execute(
                    "SELECT MIN(json_extract(payload,'$.class_date')) FROM timetable_entries "
                    "WHERE json_extract(payload,'$.class_date')>=?",
                    (today,),
                ).fetchone()
                if row and row[0]:
                    resolved_date = date.fromisoformat(str(row[0]))
                else:
                    return [], 0
            elif resolved_date is None and latest:
                row = connection.execute(
                    "SELECT MAX(json_extract(payload,'$.class_date')) FROM timetable_entries "
                    "WHERE json_extract(payload,'$.class_date') IS NOT NULL"
                ).fetchone()
                if row and row[0]:
                    resolved_date = date.fromisoformat(str(row[0]))

            if resolved_date is not None:
                clauses.append("json_extract(payload,'$.class_date')=?")
                params.append(resolved_date.isoformat())
            else:
                if date_from is not None:
                    clauses.append("json_extract(payload,'$.class_date')>=?")
                    params.append(date_from.isoformat())
                if date_to is not None:
                    clauses.append("json_extract(payload,'$.class_date')<=?")
                    params.append(date_to.isoformat())
            for field, value in (("stream", stream), ("class_name", class_name), ("subject", subject)):
                if value:
                    clauses.append(f"lower(COALESCE(json_extract(payload,'$.{field}'),'')) LIKE lower(?)")
                    params.append(f"%{value}%")
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            total = int(connection.execute(f"SELECT COUNT(*) FROM timetable_entries{where}", params).fetchone()[0])
            offset = (page - 1) * page_size
            rows = connection.execute(
                f"SELECT payload FROM timetable_entries{where} "
                "ORDER BY COALESCE(json_extract(payload,'$.class_date'),'9999-12-31'), "
                "COALESCE(json_extract(payload,'$.start_time'),'99:99:99'), "
                "lower(COALESCE(json_extract(payload,'$.stream'),'')), "
                "lower(COALESCE(json_extract(payload,'$.class_name'),'')), "
                "lower(COALESCE(json_extract(payload,'$.subject'),'')) LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [TimetableEntry.model_validate_json(row["payload"]) for row in rows], total

    def list_content(self, source_id: str | None = None) -> list[ContentItem]:
        with self.connect() as connection:
            if source_id:
                rows = connection.execute(
                    "SELECT payload FROM content_items WHERE source_id=? ORDER BY sheet_name, source_row",
                    (source_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM content_items ORDER BY sheet_name, source_row"
                ).fetchall()
        return [ContentItem.model_validate_json(row["payload"]) for row in rows]

    def list_content_page(
        self,
        *,
        page: int,
        page_size: int,
        source_id: str | None = None,
        sheet_name: str | None = None,
        content_type: str | None = None,
        stream: str | None = None,
        subject: str | None = None,
        class_name: str | None = None,
    ) -> tuple[list[ContentItem], int]:
        """Return one filtered page without deserialising the complete library."""
        clauses: list[str] = []
        params: list[object] = []
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if sheet_name:
            clauses.append("lower(sheet_name)=lower(?)")
            params.append(sheet_name)
        for json_field, value in (("content_type", content_type), ("stream", stream), ("subject", subject), ("class_name", class_name)):
            if value:
                clauses.append(f"lower(COALESCE(json_extract(payload, '$.{json_field}'),'')) LIKE lower(?)")
                params.append(f"%{value}%" if json_field != "content_type" else value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        offset = (page - 1) * page_size
        with self.connect() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM content_items{where}", params).fetchone()[0])
            rows = connection.execute(
                f"SELECT payload FROM content_items{where} ORDER BY sheet_name,source_row,lower(COALESCE(json_extract(payload,'$.title'),'')) LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [ContentItem.model_validate_json(row["payload"]) for row in rows], total

    def search_content_candidates(
        self,
        query: str,
        alias_groups: Sequence[Sequence[str]],
        limit: int = 600,
        source_id: str | None = None,
    ) -> list[ContentItem]:
        normalized_query = normalize_search_text(query)
        if not normalized_query:
            return self.list_content(source_id)
        with self.connect() as connection:
            if source_id:
                direct_rows = connection.execute(
                    "SELECT content_id FROM content_search_index WHERE source_id=? AND (raw_text LIKE ? OR normalized_text LIKE ?) LIMIT ?",
                    (source_id, f"%{query.casefold().strip()}%", f"%{normalized_query}%", limit),
                ).fetchall()
            else:
                direct_rows = connection.execute(
                    "SELECT content_id FROM content_search_index WHERE raw_text LIKE ? OR normalized_text LIKE ? LIMIT ?",
                    (f"%{query.casefold().strip()}%", f"%{normalized_query}%", limit),
                ).fetchall()
            candidate_ids = {row["content_id"] for row in direct_rows}
            token_sets: list[set[str]] = []
            for query_token in normalized_query.split():
                choices = {query_token}
                for group in alias_groups:
                    normalized_group = {normalize_search_text(value) for value in group}
                    if query_token in normalized_group:
                        choices.update(normalized_group)
                ids: set[str] = set()
                for choice in choices:
                    for word in choice.split():
                        if source_id:
                            rows = connection.execute(
                                "SELECT DISTINCT content_id FROM content_search_terms WHERE source_id=? AND (token=? OR token LIKE ?) LIMIT ?",
                                (source_id, word, f"{word}%", limit),
                            ).fetchall()
                        else:
                            rows = connection.execute(
                                "SELECT DISTINCT content_id FROM content_search_terms WHERE token=? OR token LIKE ? LIMIT ?",
                                (word, f"{word}%", limit),
                            ).fetchall()
                        ids.update(row["content_id"] for row in rows)
                token_sets.append(ids)
            non_empty = [ids for ids in token_sets if ids]
            if non_empty:
                intersection = set.intersection(*non_empty)
                candidate_ids.update(intersection or set.union(*non_empty))
            if not candidate_ids:
                from difflib import SequenceMatcher
                fuzzy_tokens: set[str] = set()
                for query_token in normalized_query.split():
                    if source_id:
                        rows = connection.execute(
                            "SELECT DISTINCT token FROM content_search_terms WHERE source_id=? AND substr(token,1,1)=? AND length(token) BETWEEN ? AND ? LIMIT 1200",
                            (source_id, query_token[:1], max(2, len(query_token)-2), len(query_token)+3),
                        ).fetchall()
                    else:
                        rows = connection.execute(
                            "SELECT DISTINCT token FROM content_search_terms WHERE substr(token,1,1)=? AND length(token) BETWEEN ? AND ? LIMIT 1200",
                            (query_token[:1], max(2, len(query_token)-2), len(query_token)+3),
                        ).fetchall()
                    scored = sorted(((SequenceMatcher(None, query_token, row["token"]).ratio(), row["token"]) for row in rows), reverse=True)
                    fuzzy_tokens.update(token for ratio, token in scored[:8] if ratio >= .70)
                if fuzzy_tokens:
                    placeholders = ",".join("?" for _ in fuzzy_tokens)
                    if source_id:
                        rows = connection.execute(
                            f"SELECT DISTINCT content_id FROM content_search_terms WHERE source_id=? AND token IN ({placeholders}) LIMIT ?",
                            (source_id, *sorted(fuzzy_tokens), limit),
                        ).fetchall()
                    else:
                        rows = connection.execute(
                            f"SELECT DISTINCT content_id FROM content_search_terms WHERE token IN ({placeholders}) LIMIT ?",
                            (*sorted(fuzzy_tokens), limit),
                        ).fetchall()
                    candidate_ids.update(row["content_id"] for row in rows)
            if not candidate_ids:
                return []
            ids = list(candidate_ids)[:limit]
            placeholders = ",".join("?" for _ in ids)
            rows = connection.execute(f"SELECT payload FROM content_items WHERE id IN ({placeholders})", ids).fetchall()
        return [ContentItem.model_validate_json(row["payload"]) for row in rows]

    def replace_test_records(self, source_id: str, records: Sequence[TestRecord]) -> list[TestRecord]:
        now = datetime.now(UTC)
        baseline_key = f"test_baseline:{source_id}"
        with self.connect() as connection:
            baseline_exists = connection.execute(
                "SELECT 1 FROM app_metadata WHERE key=?", (baseline_key,)
            ).fetchone() is not None
            existing_rows = connection.execute(
                "SELECT id,first_seen_at FROM test_records WHERE source_id=?", (source_id,)
            ).fetchall()
            existing = {row["id"]: row["first_seen_at"] for row in existing_rows}
            new_records: list[TestRecord] = []
            incoming_ids = {record.id for record in records}
            for record in records:
                first_seen = (
                    datetime.fromisoformat(existing[record.id])
                    if record.id in existing
                    else (now if baseline_exists else datetime(1970, 1, 1, tzinfo=UTC))
                )
                stored = record.model_copy(update={"first_seen_at": first_seen, "last_seen_at": now})
                connection.execute(
                    """INSERT INTO test_records(id,source_id,workbook_name,sheet_name,source_row,payload,fingerprint,first_seen_at,last_seen_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        workbook_name=excluded.workbook_name,
                        sheet_name=excluded.sheet_name,
                        source_row=excluded.source_row,
                        payload=excluded.payload,
                        fingerprint=excluded.fingerprint,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        stored.id, stored.source_id, stored.workbook_name, stored.sheet_name,
                        stored.source_row, stored.model_dump_json(), stored.fingerprint,
                        first_seen.isoformat(), now.isoformat(),
                    ),
                )
                if baseline_exists and record.id not in existing:
                    new_records.append(stored)
            if incoming_ids:
                placeholders = ",".join("?" for _ in incoming_ids)
                connection.execute(
                    f"DELETE FROM test_records WHERE source_id=? AND id NOT IN ({placeholders})",
                    (source_id, *sorted(incoming_ids)),
                )
            else:
                connection.execute("DELETE FROM test_records WHERE source_id=?", (source_id,))
            connection.execute(
                "INSERT INTO app_metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (baseline_key, now.isoformat()),
            )
        return new_records

    def list_test_records(
        self,
        source_id: str | None = None,
        sheet_names: Sequence[str] | None = None,
    ) -> list[TestRecord]:
        sql = "SELECT payload,first_seen_at,last_seen_at FROM test_records"
        params: list[object] = []
        clauses: list[str] = []
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if sheet_names:
            placeholders = ",".join("?" for _ in sheet_names)
            clauses.append(f"sheet_name IN ({placeholders})")
            params.extend(sheet_names)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY sheet_name,source_row"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        result: list[TestRecord] = []
        for row in rows:
            item = TestRecord.model_validate_json(row["payload"])
            result.append(item.model_copy(update={
                "first_seen_at": datetime.fromisoformat(row["first_seen_at"]),
                "last_seen_at": datetime.fromisoformat(row["last_seen_at"]),
            }))
        return result

    def get_test_records(self, record_ids: Sequence[str]) -> list[TestRecord]:
        if not record_ids:
            return []
        placeholders = ",".join("?" for _ in record_ids)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT payload,first_seen_at,last_seen_at FROM test_records WHERE id IN ({placeholders})",
                list(record_ids),
            ).fetchall()
        result: list[TestRecord] = []
        for row in rows:
            item = TestRecord.model_validate_json(row["payload"])
            result.append(item.model_copy(update={
                "first_seen_at": datetime.fromisoformat(row["first_seen_at"]),
                "last_seen_at": datetime.fromisoformat(row["last_seen_at"]),
            }))
        return result

    def list_changes(self, limit: int = 500) -> list[ChangeRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM changes ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            ChangeRecord(
                id=row["id"],
                source_id=row["source_id"],
                workbook_name=row["workbook_name"],
                sheet_name=row["sheet_name"],
                coordinate=row["coordinate"],
                change_type=row["change_type"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                detected_at=datetime.fromisoformat(row["detected_at"]),
                field_name=row["field_name"] if "field_name" in row.keys() else None,
                row_label=row["row_label"] if "row_label" in row.keys() else None,
            )
            for row in rows
        ]

    def upsert_notification_rule(self, rule: NotificationRule) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO notification_rules(id,payload,created_at) VALUES(?,?,?)
                ON CONFLICT(id) DO UPDATE SET payload=excluded.payload
                """,
                (rule.id, rule.model_dump_json(), rule.created_at.isoformat()),
            )

    def list_notification_rules(self) -> list[NotificationRule]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM notification_rules ORDER BY created_at"
            ).fetchall()
        return [NotificationRule.model_validate_json(row["payload"]) for row in rows]

    def get_notification_rule(self, rule_id: str) -> NotificationRule | None:
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM notification_rules WHERE id=?", (rule_id,)).fetchone()
        return NotificationRule.model_validate_json(row["payload"]) if row else None

    def delete_notification_rule(self, rule_id: str, *, delete_history: bool = True) -> bool:
        with self.connect() as connection:
            if delete_history:
                connection.execute(
                    "DELETE FROM notification_deliveries WHERE rule_id=?",
                    (rule_id,),
                )
            cursor = connection.execute(
                "DELETE FROM notification_rules WHERE id=?",
                (rule_id,),
            )
            return cursor.rowcount > 0

    def insert_notification_delivery(self, delivery: NotificationDelivery) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO notification_deliveries(
                id,rule_id,rule_name,channel,recipient,status,message,error,attempted_at,scheduled_for,is_test,dedupe_key
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (delivery.id, delivery.rule_id, delivery.rule_name, delivery.channel, delivery.recipient,
                 delivery.status, delivery.message, delivery.error, delivery.attempted_at.isoformat(),
                 delivery.scheduled_for.isoformat() if delivery.scheduled_for else None,
                 int(delivery.is_test), delivery.dedupe_key),
            )
            return cursor.rowcount > 0

    def list_notification_deliveries(self, limit: int = 50) -> list[NotificationDelivery]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM notification_deliveries ORDER BY attempted_at DESC LIMIT ?", (limit,)).fetchall()
        return [NotificationDelivery(
            id=row["id"], rule_id=row["rule_id"], rule_name=row["rule_name"], channel=row["channel"],
            recipient=row["recipient"], status=row["status"], message=row["message"], error=row["error"],
            attempted_at=datetime.fromisoformat(row["attempted_at"]),
            scheduled_for=datetime.fromisoformat(row["scheduled_for"]) if row["scheduled_for"] else None,
            is_test=bool(row["is_test"]), dedupe_key=row["dedupe_key"]
        ) for row in rows]

    def notification_delivery_exists(self, dedupe_key: str) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT 1 FROM notification_deliveries WHERE dedupe_key=?", (dedupe_key,)).fetchone() is not None

    def record_sync(
        self,
        source_id: str,
        status: str,
        live_data: bool,
        started_at: datetime,
        completed_at: datetime,
        warning_count: int,
        error: str | None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_runs(source_id,status,live_data,started_at,completed_at,warning_count,error)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    source_id,
                    status,
                    int(live_data),
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    warning_count,
                    error,
                ),
            )

    def dashboard_counts(self) -> dict[str, int | str | None]:
        today = datetime.now(INDIA_TIMEZONE).date().isoformat()
        with self.connect() as connection:
            source_count = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            profile_payloads = [
                row[0] for row in connection.execute("SELECT payload FROM workbook_profiles")
            ]
            if profile_payloads:
                tab_count = sum(len(json.loads(payload).get("tabs", [])) for payload in profile_payloads)
            else:
                tab_count = connection.execute(
                    "SELECT COUNT(*) FROM (SELECT DISTINCT source_id, sheet_name FROM cells)"
                ).fetchone()[0]
            timetable_count = connection.execute(
                "SELECT COUNT(*) FROM timetable_entries"
            ).fetchone()[0]
            content_count = connection.execute("SELECT COUNT(*) FROM content_items").fetchone()[0]
            changes_today = connection.execute(
                "SELECT COUNT(*) FROM changes WHERE substr(detected_at,1,10)=?", (today,)
            ).fetchone()[0]
            sync_errors = connection.execute(
                "SELECT COUNT(*) FROM sources WHERE last_sync_status='error'"
            ).fetchone()[0]
            last_sync_row = connection.execute(
                "SELECT MAX(last_sync_at) FROM sources WHERE last_sync_status='success'"
            ).fetchone()[0]
            videos = connection.execute(
                "SELECT COUNT(*) FROM content_items WHERE json_extract(payload,'$.content_type')='video'"
            ).fetchone()[0]
            pdfs = connection.execute(
                "SELECT COUNT(*) FROM content_items WHERE json_extract(payload,'$.content_type')='pdf'"
            ).fetchone()[0]
        return {
            "connected_sources": source_count,
            "tabs_scanned": tab_count,
            "timetable_entries": timetable_count,
            "content_items": content_count,
            "videos": videos,
            "pdfs": pdfs,
            "changes_today": changes_today,
            "sync_errors": sync_errors,
            "last_successful_sync": last_sync_row,
        }


    def create_qr_code(
        self,
        *,
        qr_id: str,
        name: str,
        slug: str,
        qr_type: str,
        tracking_mode: str,
        identity_mode: str,
        target_url: str,
        payload_json: str,
        public_base_url: str | None,
        short_url: str | None,
        design_json: str,
        experience_json: str,
        created_at: datetime,
        template_id: str | None = None,
    ) -> QrCodeRecord:
        stamp = created_at.astimezone(UTC).isoformat()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO qr_codes(id,name,slug,qr_type,tracking_mode,identity_mode,target_url,payload_json,public_base_url,short_url,design_json,experience_json,template_id,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (qr_id, name, slug, qr_type, tracking_mode, identity_mode, target_url, payload_json, public_base_url, short_url, design_json, experience_json, template_id, stamp, stamp),
            )
        return self.get_qr_code(qr_id)  # type: ignore[return-value]

    def create_qr_template(
        self,
        *,
        template_id: str,
        name: str,
        description: str,
        tracking_mode: str,
        identity_mode: str,
        design_json: str,
        experience_json: str,
        is_default: bool,
        created_at: datetime,
    ) -> QrTemplateRecord:
        stamp = created_at.astimezone(UTC).isoformat()
        with self.connect() as connection:
            if is_default:
                connection.execute("UPDATE qr_templates SET is_default=0")
            connection.execute(
                """INSERT INTO qr_templates(id,name,description,tracking_mode,identity_mode,design_json,experience_json,is_default,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (template_id, name, description, tracking_mode, identity_mode, design_json, experience_json, 1 if is_default else 0, stamp, stamp),
            )
        return self.get_qr_template(template_id)  # type: ignore[return-value]

    def list_qr_templates(self) -> list[QrTemplateRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT t.id,t.name,t.description,t.tracking_mode,t.identity_mode,t.design_json,t.experience_json,
                          t.is_default,t.created_at,t.updated_at,COUNT(q.id) AS qr_count
                   FROM qr_templates t LEFT JOIN qr_codes q ON q.template_id=t.id
                   GROUP BY t.id ORDER BY t.is_default DESC,t.updated_at DESC,t.name"""
            ).fetchall()
        return [self._row_to_qr_template(row) for row in rows]

    def get_qr_template(self, template_id: str) -> QrTemplateRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT t.id,t.name,t.description,t.tracking_mode,t.identity_mode,t.design_json,t.experience_json,
                          t.is_default,t.created_at,t.updated_at,COUNT(q.id) AS qr_count
                   FROM qr_templates t LEFT JOIN qr_codes q ON q.template_id=t.id
                   WHERE t.id=? GROUP BY t.id""",
                (template_id,),
            ).fetchone()
        return self._row_to_qr_template(row) if row else None

    def update_qr_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tracking_mode: str | None = None,
        identity_mode: str | None = None,
        design_json: str | None = None,
        experience_json: str | None = None,
        is_default: bool | None = None,
    ) -> QrTemplateRecord | None:
        fields: list[str] = []
        values: list[object] = []
        for column, value in (
            ("name", name), ("description", description), ("tracking_mode", tracking_mode),
            ("identity_mode", identity_mode), ("design_json", design_json), ("experience_json", experience_json),
        ):
            if value is not None:
                fields.append(f"{column}=?")
                values.append(value)
        with self.connect() as connection:
            exists = connection.execute("SELECT 1 FROM qr_templates WHERE id=?", (template_id,)).fetchone()
            if not exists:
                return None
            if is_default is not None:
                if is_default:
                    connection.execute("UPDATE qr_templates SET is_default=0")
                fields.append("is_default=?")
                values.append(1 if is_default else 0)
            if fields:
                fields.append("updated_at=?")
                values.append(datetime.now(UTC).isoformat())
                values.append(template_id)
                connection.execute(f"UPDATE qr_templates SET {','.join(fields)} WHERE id=?", tuple(values))
        return self.get_qr_template(template_id)

    def delete_qr_template(self, template_id: str) -> bool:
        with self.connect() as connection:
            exists = connection.execute("SELECT 1 FROM qr_templates WHERE id=?", (template_id,)).fetchone()
            if not exists:
                return False
            connection.execute("UPDATE qr_codes SET template_id=NULL WHERE template_id=?", (template_id,))
            connection.execute("DELETE FROM qr_templates WHERE id=?", (template_id,))
        return True

    def create_qr_codes_bulk(self, records: list[dict[str, object]]) -> list[QrCodeRecord]:
        if not records:
            return []
        with self.connect() as connection:
            for record in records:
                connection.execute(
                    """INSERT INTO qr_codes(id,name,slug,qr_type,tracking_mode,identity_mode,target_url,payload_json,
                       public_base_url,short_url,design_json,experience_json,template_id,active,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (
                        record["id"], record["name"], record["slug"], record.get("qr_type", "url"),
                        record["tracking_mode"], record["identity_mode"], record["target_url"], record["payload_json"],
                        record.get("public_base_url"), None, record["design_json"], record["experience_json"],
                        record["template_id"], record["created_at"], record["created_at"],
                    ),
                )
        return [code for code in (self.get_qr_code(str(record["id"])) for record in records) if code is not None]

    def qr_asset_reference_count(self, asset_id: str) -> int:
        if not asset_id:
            return 0
        with self.connect() as connection:
            row = connection.execute(
                """SELECT
                    (SELECT COUNT(*) FROM qr_codes WHERE
                      (json_valid(design_json)=1 AND json_extract(design_json,'$.logo_asset_id')=?) OR
                      (json_valid(experience_json)=1 AND json_extract(experience_json,'$.asset_id')=?)) +
                    (SELECT COUNT(*) FROM qr_templates WHERE
                      (json_valid(design_json)=1 AND json_extract(design_json,'$.logo_asset_id')=?) OR
                      (json_valid(experience_json)=1 AND json_extract(experience_json,'$.asset_id')=?)) AS refs""",
                (asset_id, asset_id, asset_id, asset_id),
            ).fetchone()
        return int(row["refs"] or 0) if row else 0

    def list_qr_codes(self) -> list[QrCodeRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT q.id,q.name,q.slug,q.qr_type,q.tracking_mode,q.identity_mode,q.target_url,q.payload_json,q.public_base_url,q.short_url,q.design_json,q.experience_json,q.template_id,t.name AS template_name,q.active,q.created_at,q.updated_at,
                       SUM(CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN 1 ELSE 0 END) AS total_scans,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN s.visitor_hash END) AS unique_visitors,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.scanner_email != '' THEN lower(s.scanner_email) END) AS unique_emails,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.country != 'Unknown' THEN s.country END) AS country_count,
                       SUM(CASE WHEN s.confirmed=0 THEN 1 ELSE 0 END) AS legacy_scans
                FROM qr_codes q
                LEFT JOIN qr_templates t ON t.id=q.template_id
                LEFT JOIN qr_scans s ON s.qr_id=q.id
                GROUP BY q.id
                ORDER BY q.created_at DESC
                """
            ).fetchall()
        return [self._row_to_qr_code(row) for row in rows]

    def get_qr_code(self, qr_id: str) -> QrCodeRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT q.id,q.name,q.slug,q.qr_type,q.tracking_mode,q.identity_mode,q.target_url,q.payload_json,q.public_base_url,q.short_url,q.design_json,q.experience_json,q.template_id,t.name AS template_name,q.active,q.created_at,q.updated_at,
                       SUM(CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN 1 ELSE 0 END) AS total_scans,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN s.visitor_hash END) AS unique_visitors,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.scanner_email != '' THEN lower(s.scanner_email) END) AS unique_emails,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.country != 'Unknown' THEN s.country END) AS country_count,
                       SUM(CASE WHEN s.confirmed=0 THEN 1 ELSE 0 END) AS legacy_scans
                FROM qr_codes q LEFT JOIN qr_templates t ON t.id=q.template_id LEFT JOIN qr_scans s ON s.qr_id=q.id
                WHERE q.id=? GROUP BY q.id
                """,
                (qr_id,),
            ).fetchone()
        return self._row_to_qr_code(row) if row else None

    def get_qr_code_by_slug(self, slug: str) -> QrCodeRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT q.id,q.name,q.slug,q.qr_type,q.tracking_mode,q.identity_mode,q.target_url,q.payload_json,q.public_base_url,q.short_url,q.design_json,q.experience_json,q.template_id,t.name AS template_name,q.active,q.created_at,q.updated_at,
                       SUM(CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN 1 ELSE 0 END) AS total_scans,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' THEN s.visitor_hash END) AS unique_visitors,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.scanner_email != '' THEN lower(s.scanner_email) END) AS unique_emails,
                       COUNT(DISTINCT CASE WHEN s.confirmed=1 AND s.device_type != 'bot' AND s.country != 'Unknown' THEN s.country END) AS country_count,
                       SUM(CASE WHEN s.confirmed=0 THEN 1 ELSE 0 END) AS legacy_scans
                FROM qr_codes q LEFT JOIN qr_templates t ON t.id=q.template_id LEFT JOIN qr_scans s ON s.qr_id=q.id
                WHERE q.slug=? GROUP BY q.id
                """,
                (slug,),
            ).fetchone()
        return self._row_to_qr_code(row) if row else None

    def update_qr_code(
        self,
        qr_id: str,
        *,
        name: str | None = None,
        qr_type: str | None = None,
        tracking_mode: str | None = None,
        identity_mode: str | None = None,
        target_url: str | None = None,
        payload_json: str | None = None,
        design_json: str | None = None,
        experience_json: str | None = None,
    ) -> QrCodeRecord | None:
        fields: list[str] = []
        values: list[object] = []
        for column, value in (
            ("name", name), ("qr_type", qr_type), ("tracking_mode", tracking_mode),
            ("identity_mode", identity_mode), ("target_url", target_url), ("payload_json", payload_json),
            ("design_json", design_json), ("experience_json", experience_json),
        ):
            if value is not None:
                fields.append(f"{column}=?")
                values.append(value)
        if not fields:
            return self.get_qr_code(qr_id)
        fields.append("updated_at=?")
        values.append(datetime.now(UTC).isoformat())
        values.append(qr_id)
        with self.connect() as connection:
            updated = connection.execute(
                f"UPDATE qr_codes SET {','.join(fields)} WHERE id=?",
                tuple(values),
            ).rowcount
        return self.get_qr_code(qr_id) if updated else None

    def set_qr_code_active(self, qr_id: str, active: bool) -> QrCodeRecord | None:
        with self.connect() as connection:
            updated = connection.execute(
                "UPDATE qr_codes SET active=?,updated_at=? WHERE id=?",
                (1 if active else 0, datetime.now(UTC).isoformat(), qr_id),
            ).rowcount
        return self.get_qr_code(qr_id) if updated else None

    def clear_qr_scans(self, qr_id: str) -> int | None:
        with self.connect() as connection:
            exists = connection.execute("SELECT 1 FROM qr_codes WHERE id=?", (qr_id,)).fetchone()
            if not exists:
                return None
            deleted = connection.execute("DELETE FROM qr_scans WHERE qr_id=?", (qr_id,)).rowcount
            connection.execute(
                "UPDATE qr_codes SET updated_at=? WHERE id=?",
                (datetime.now(UTC).isoformat(), qr_id),
            )
            return int(deleted)

    def delete_qr_code(self, qr_id: str) -> bool:
        with self.connect() as connection:
            deleted = connection.execute("DELETE FROM qr_codes WHERE id=?", (qr_id,)).rowcount
            return bool(deleted)

    def record_qr_scan(
        self,
        *,
        qr_id: str,
        scanned_at: datetime,
        visitor_hash: str,
        country: str,
        device_type: str,
        browser: str,
        operating_system: str = "Other",
        platform: str = "Direct / QR",
        source_confidence: str = "unknown",
        referrer_host: str = "",
        language: str = "",
        timezone: str = "",
        scanner_email: str = "",
        device_model: str = "",
        client_platform: str = "",
        telemetry_json: str = "{}",
        screen_width: int | None = None,
        screen_height: int | None = None,
        event_hash: str | None = None,
        confirmed: bool = True,
    ) -> int | None:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO qr_scans(
                    qr_id,scanned_at,visitor_hash,event_hash,confirmed,country,device_type,browser,
                    operating_system,platform,source_confidence,referrer_host,language,timezone,scanner_email,
                    device_model,client_platform,telemetry_json,screen_width,screen_height
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    qr_id, scanned_at.astimezone(UTC).isoformat(), visitor_hash, event_hash,
                    1 if confirmed else 0, country, device_type, browser, operating_system,
                    platform, source_confidence, referrer_host, language, timezone, scanner_email,
                    device_model, client_platform, telemetry_json, screen_width, screen_height,
                ),
            )
            if cursor.rowcount <= 0:
                return None
            return int(cursor.lastrowid)

    def qr_analytics(self, qr_id: str | None = None, recent_limit: int = 50) -> QrAnalyticsSummary:
        scope = "s.qr_id=?" if qr_id else "1=1"
        scope_params: tuple[object, ...] = (qr_id,) if qr_id else ()
        india_today = datetime.now(INDIA_TIMEZONE).date()
        today = india_today.isoformat()
        seven_days = (india_today - timedelta(days=6)).isoformat()
        thirty_days = (india_today - timedelta(days=29)).isoformat()
        india_day = "date(s.scanned_at, '+5 hours', '+30 minutes')"
        human = "s.confirmed=1 AND s.device_type!='bot'"

        with self.connect() as connection:
            qr_where = "WHERE id=?" if qr_id else ""
            qr_params = (qr_id,) if qr_id else ()
            qr_counts = connection.execute(
                f"SELECT COUNT(*) AS total, SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) AS active FROM qr_codes {qr_where}",
                qr_params,
            ).fetchone()

            totals = connection.execute(
                f"""SELECT
                    SUM(CASE WHEN {human} THEN 1 ELSE 0 END) AS total_scans,
                    COUNT(DISTINCT CASE WHEN {human} THEN s.visitor_hash END) AS unique_visitors,
                    COUNT(DISTINCT CASE WHEN {human} AND s.scanner_email!='' THEN lower(s.scanner_email) END) AS unique_emails,
                    SUM(CASE WHEN {human} AND s.scanner_email!='' THEN 1 ELSE 0 END) AS identified_scans,
                    SUM(CASE WHEN {human} AND s.scanner_email='' THEN 1 ELSE 0 END) AS anonymous_scans,
                    SUM(CASE WHEN {human} AND {india_day}=? THEN 1 ELSE 0 END) AS scans_today,
                    SUM(CASE WHEN {human} AND {india_day}>=? THEN 1 ELSE 0 END) AS scans_7days,
                    SUM(CASE WHEN {human} AND {india_day}>=? THEN 1 ELSE 0 END) AS scans_30days,
                    SUM(CASE WHEN s.confirmed=1 AND s.device_type='bot' THEN 1 ELSE 0 END) AS bot_scans,
                    SUM(CASE WHEN s.confirmed=0 THEN 1 ELSE 0 END) AS legacy_scans
                FROM qr_scans s
                WHERE {scope}""",
                (today, seven_days, thirty_days, *scope_params),
            ).fetchone()

            countries = connection.execute(
                f"""SELECT s.country,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.country ORDER BY count DESC,s.country""",
                scope_params,
            ).fetchall()
            devices = connection.execute(
                f"""SELECT s.device_type,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.device_type ORDER BY count DESC,s.device_type""",
                scope_params,
            ).fetchall()
            browsers = connection.execute(
                f"""SELECT s.browser,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.browser ORDER BY count DESC,s.browser""",
                scope_params,
            ).fetchall()
            operating_systems = connection.execute(
                f"""SELECT s.operating_system,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.operating_system ORDER BY count DESC,s.operating_system""",
                scope_params,
            ).fetchall()
            platforms = connection.execute(
                f"""SELECT s.platform,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.platform ORDER BY count DESC,s.platform""",
                scope_params,
            ).fetchall()
            device_models = connection.execute(
                f"""SELECT CASE WHEN trim(s.device_model)='' THEN 'Model unavailable' ELSE s.device_model END AS device_model,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY device_model ORDER BY count DESC,device_model""",
                scope_params,
            ).fetchall()
            memory_classes = connection.execute(
                f"""SELECT
                    CASE
                      WHEN json_valid(s.telemetry_json)=0 OR json_extract(s.telemetry_json,'$.device_memory_gb') IS NULL THEN 'Unavailable'
                      ELSE printf('%g GB', CAST(json_extract(s.telemetry_json,'$.device_memory_gb') AS REAL))
                    END AS label,
                    COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY label ORDER BY count DESC,label""",
                scope_params,
            ).fetchall()
            cpu_cores = connection.execute(
                f"""SELECT
                    CASE
                      WHEN json_valid(s.telemetry_json)=0 OR json_extract(s.telemetry_json,'$.hardware_concurrency') IS NULL THEN 'Unavailable'
                      ELSE printf('%d cores', CAST(json_extract(s.telemetry_json,'$.hardware_concurrency') AS INTEGER))
                    END AS label,
                    COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY label ORDER BY count DESC,label""",
                scope_params,
            ).fetchall()
            connection_types = connection.execute(
                f"""SELECT
                    CASE WHEN json_valid(s.telemetry_json)=0 THEN 'Unavailable' ELSE
                      COALESCE(
                        NULLIF(json_extract(s.telemetry_json,'$.effective_connection_type'),''),
                        NULLIF(json_extract(s.telemetry_json,'$.connection_type'),''),
                        'Unavailable'
                      )
                    END AS label,
                    COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY label ORDER BY count DESC,label""",
                scope_params,
            ).fetchall()
            top_devices = connection.execute(
                f"""SELECT s.visitor_hash,COUNT(*) AS scans,MIN(s.scanned_at) AS first_seen,MAX(s.scanned_at) AS last_seen,
                           MAX(s.device_type) AS device_type,MAX(s.operating_system) AS operating_system,
                           MAX(s.browser) AS browser,MAX(s.device_model) AS device_model,
                           MAX(s.scanner_email) AS scanner_email,MAX(s.client_platform) AS client_platform,
                           MAX(s.language) AS language,MAX(s.timezone) AS timezone,
                           MAX(s.telemetry_json) AS telemetry_json,
                           MAX(s.screen_width) AS screen_width,MAX(s.screen_height) AS screen_height,
                           COUNT(DISTINCT s.country) AS countries,COUNT(DISTINCT s.qr_id) AS qr_codes
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.visitor_hash ORDER BY scans DESC,last_seen DESC LIMIT 50""",
                scope_params,
            ).fetchall()
            confidence = connection.execute(
                f"""SELECT s.source_confidence,COUNT(*) AS count
                FROM qr_scans s WHERE {scope} AND {human}
                GROUP BY s.source_confidence ORDER BY count DESC,s.source_confidence""",
                scope_params,
            ).fetchall()
            daily = connection.execute(
                f"""SELECT {india_day} AS day,COUNT(*) AS count
                FROM qr_scans s
                WHERE {scope} AND {human} AND {india_day}>=?
                GROUP BY day ORDER BY day""",
                (*scope_params, thirty_days),
            ).fetchall()
            recent = connection.execute(
                f"""SELECT s.id,s.qr_id,q.name AS qr_name,s.scanned_at,s.country,s.device_type,s.browser,
                           s.operating_system,s.device_model,s.visitor_hash,s.scanner_email,s.platform,s.source_confidence,s.referrer_host,
                           s.language,s.timezone,s.client_platform,s.telemetry_json,s.screen_width,s.screen_height
                FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id
                WHERE {scope} AND {human}
                ORDER BY s.scanned_at DESC LIMIT ?""",
                (*scope_params, max(1, min(recent_limit, 200))),
            ).fetchall()

        return QrAnalyticsSummary(
            total_qr_codes=int(qr_counts['total'] or 0),
            active_qr_codes=int(qr_counts['active'] or 0),
            total_scans=int(totals['total_scans'] or 0),
            unique_visitors=int(totals['unique_visitors'] or 0),
            unique_emails=int(totals['unique_emails'] or 0),
            identified_scans=int(totals['identified_scans'] or 0),
            anonymous_scans=int(totals['anonymous_scans'] or 0),
            scans_today=int(totals['scans_today'] or 0),
            scans_7days=int(totals['scans_7days'] or 0),
            scans_30days=int(totals['scans_30days'] or 0),
            bot_scans=int(totals['bot_scans'] or 0),
            legacy_scans=int(totals['legacy_scans'] or 0),
            countries={str(row['country']): int(row['count']) for row in countries},
            devices={str(row['device_type']): int(row['count']) for row in devices},
            browsers={str(row['browser']): int(row['count']) for row in browsers},
            operating_systems={str(row['operating_system']): int(row['count']) for row in operating_systems},
            device_models={str(row['device_model']): int(row['count']) for row in device_models},
            memory_classes={str(row['label']): int(row['count']) for row in memory_classes},
            cpu_cores={str(row['label']): int(row['count']) for row in cpu_cores},
            connection_types={str(row['label']): int(row['count']) for row in connection_types},
            platforms={str(row['platform']): int(row['count']) for row in platforms},
            attribution_confidence={str(row['source_confidence']): int(row['count']) for row in confidence},
            daily={str(row['day']): int(row['count']) for row in daily if row['day']},
            top_devices=[
                QrDeviceSummary(
                    device_id=f"Device {str(row['visitor_hash'])[:8].upper()}",
                    scans=int(row['scans'] or 0),
                    first_seen=datetime.fromisoformat(str(row['first_seen'])),
                    last_seen=datetime.fromisoformat(str(row['last_seen'])),
                    device_type=str(row['device_type'] or "Other"),
                    operating_system=str(row['operating_system'] or "Other"),
                    browser=str(row['browser'] or "Other"),
                    device_model=str(row['device_model'] or ""),
                    scanner_email=str(row['scanner_email'] or ""),
                    client_platform=str(row['client_platform'] or ""),
                    language=str(row['language'] or ""),
                    timezone=str(row['timezone'] or ""),
                    screen_resolution=(f"{int(row['screen_width'])}×{int(row['screen_height'])}" if row['screen_width'] and row['screen_height'] else ""),
                    countries=int(row['countries'] or 0),
                    qr_codes=int(row['qr_codes'] or 0),
                    browser_version=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "browser_version"),
                    platform_version=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "platform_version"),
                    architecture=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "architecture"),
                    bitness=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "bitness"),
                    device_memory_gb=_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "device_memory_gb"),
                    hardware_concurrency=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "hardware_concurrency")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "hardware_concurrency") is not None else None),
                    max_touch_points=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "max_touch_points")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "max_touch_points") is not None else None),
                    pixel_ratio=_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "pixel_ratio"),
                    viewport=_qr_viewport(_qr_telemetry_object(row['telemetry_json'])),
                    viewport_width=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_width")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_width") is not None else None),
                    viewport_height=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_height")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_height") is not None else None),
                    color_depth=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "color_depth")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "color_depth") is not None else None),
                    connection=_qr_network_label(_qr_telemetry_object(row['telemetry_json'])),
                    network_quality=_qr_network_quality(_qr_telemetry_object(row['telemetry_json'])),
                    form_factors=_qr_form_factors(_qr_telemetry_object(row['telemetry_json'])),
                    screen_orientation=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "screen_orientation"),
                    browser_vendor=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "browser_vendor"),
                    cookies_enabled=_qr_telemetry_bool(_qr_telemetry_object(row['telemetry_json']), "cookies_enabled"),
                    standalone=_qr_telemetry_bool(_qr_telemetry_object(row['telemetry_json']), "standalone"),
                    input_capability=_qr_input_capability(_qr_telemetry_object(row['telemetry_json'])),
                    color_gamut=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "color_gamut"),
                    languages=_qr_languages(_qr_telemetry_object(row['telemetry_json'])),
                    timezone_offset_minutes=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "timezone_offset_minutes")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "timezone_offset_minutes") is not None else None),
                ) for row in top_devices
            ],
            recent_scans=[
                QrScanRecord(
                    id=int(row['id']),
                    qr_id=str(row['qr_id']),
                    qr_name=str(row['qr_name']),
                    scanned_at=datetime.fromisoformat(str(row['scanned_at'])),
                    country=str(row['country']),
                    device_type=str(row['device_type']),
                    browser=str(row['browser']),
                    operating_system=str(row['operating_system']),
                    device_model=str(row['device_model'] or ""),
                    device_id=f"Device {str(row['visitor_hash'])[:8].upper()}",
                    scanner_email=str(row['scanner_email'] or ""),
                    platform=str(row['platform']),
                    source_confidence=str(row['source_confidence']),
                    referrer_host=str(row['referrer_host'] or ""),
                    language=str(row['language'] or ""),
                    timezone=str(row['timezone'] or ""),
                    screen_resolution=(f"{int(row['screen_width'])}×{int(row['screen_height'])}" if row['screen_width'] and row['screen_height'] else ""),
                    client_platform=str(row['client_platform'] or ""),
                    browser_version=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "browser_version"),
                    platform_version=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "platform_version"),
                    architecture=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "architecture"),
                    bitness=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "bitness"),
                    device_memory_gb=_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "device_memory_gb"),
                    hardware_concurrency=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "hardware_concurrency")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "hardware_concurrency") is not None else None),
                    max_touch_points=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "max_touch_points")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "max_touch_points") is not None else None),
                    pixel_ratio=_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "pixel_ratio"),
                    viewport=_qr_viewport(_qr_telemetry_object(row['telemetry_json'])),
                    viewport_width=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_width")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_width") is not None else None),
                    viewport_height=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_height")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "viewport_height") is not None else None),
                    color_depth=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "color_depth")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "color_depth") is not None else None),
                    connection=_qr_network_label(_qr_telemetry_object(row['telemetry_json'])),
                    network_quality=_qr_network_quality(_qr_telemetry_object(row['telemetry_json'])),
                    form_factors=_qr_form_factors(_qr_telemetry_object(row['telemetry_json'])),
                    screen_orientation=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "screen_orientation"),
                    browser_vendor=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "browser_vendor"),
                    cookies_enabled=_qr_telemetry_bool(_qr_telemetry_object(row['telemetry_json']), "cookies_enabled"),
                    standalone=_qr_telemetry_bool(_qr_telemetry_object(row['telemetry_json']), "standalone"),
                    input_capability=_qr_input_capability(_qr_telemetry_object(row['telemetry_json'])),
                    color_gamut=_qr_telemetry_text(_qr_telemetry_object(row['telemetry_json']), "color_gamut"),
                    languages=_qr_languages(_qr_telemetry_object(row['telemetry_json'])),
                    timezone_offset_minutes=(int(_qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "timezone_offset_minutes")) if _qr_telemetry_number(_qr_telemetry_object(row['telemetry_json']), "timezone_offset_minutes") is not None else None),
                )
                for row in recent
            ],
        )

    def qr_scan_rows(self, qr_id: str | None = None, limit: int = 5000) -> list[sqlite3.Row]:
        with self.connect() as connection:
            if qr_id:
                return connection.execute(
                    "SELECT s.*,q.name AS qr_name FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id WHERE s.qr_id=? ORDER BY s.scanned_at DESC LIMIT ?",
                    (qr_id, max(1, min(limit, 20000))),
                ).fetchall()
            return connection.execute(
                "SELECT s.*,q.name AS qr_name FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id ORDER BY s.scanned_at DESC LIMIT ?",
                (max(1, min(limit, 20000)),),
            ).fetchall()

    @staticmethod
    def _normalize_qr_design(raw: object) -> QrDesignSettings:
        data = raw if isinstance(raw, dict) else {}
        clean = QrDesignSettings().model_dump()
        clean.update({key: value for key, value in data.items() if key in clean})

        if clean.get("dot_style") not in {"square", "rounded", "dots"}:
            clean["dot_style"] = "rounded"
        if clean.get("marker_border_style") not in {"square", "rounded", "circle"}:
            clean["marker_border_style"] = "rounded"
        if clean.get("marker_center_style") not in {"square", "rounded", "circle"}:
            clean["marker_center_style"] = "square"
        if clean.get("frame_style") not in {"none", "text", "badge"}:
            clean["frame_style"] = "text"
        try:
            clean["logo_scale_percent"] = max(8, min(28, int(clean.get("logo_scale_percent") or 18)))
        except (TypeError, ValueError):
            clean["logo_scale_percent"] = 18
        frame_text = clean.get("frame_text")
        if frame_text is not None:
            clean["frame_text"] = str(frame_text)[:42]
        logo_asset = clean.get("logo_asset_id")
        if logo_asset is not None:
            clean["logo_asset_id"] = str(logo_asset)[:80]
        return QrDesignSettings.model_validate(clean)

    @staticmethod
    def _normalize_qr_experience(raw: object) -> QrScanExperience:
        data = raw if isinstance(raw, dict) else {}
        clean = QrScanExperience().model_dump()
        clean.update({key: value for key, value in data.items() if key in clean})

        if clean.get("mode") not in {"brand", "logo", "page"}:
            clean["mode"] = "brand"
        if clean.get("image_fit") not in {"cover", "contain"}:
            clean["image_fit"] = "cover"
        try:
            # v1.0.19 allowed values down to 350 ms. Current branded scan
            # pages require at least 650 ms, so older saved campaigns are
            # upgraded in-memory instead of making GET /qr-codes return 500.
            clean["redirect_delay_ms"] = max(650, min(5000, int(clean.get("redirect_delay_ms") or 900)))
        except (TypeError, ValueError):
            clean["redirect_delay_ms"] = 900
        try:
            clean["logo_scale_percent"] = max(15, min(55, int(clean.get("logo_scale_percent") or 28)))
        except (TypeError, ValueError):
            clean["logo_scale_percent"] = 28
        try:
            clean["image_scale_percent"] = max(40, min(100, int(clean.get("image_scale_percent") or 100)))
        except (TypeError, ValueError):
            clean["image_scale_percent"] = 100
        for key, limit in (("asset_id", 80), ("title", 80), ("message", 160)):
            value = clean.get(key)
            if value is not None:
                clean[key] = str(value)[:limit]
        return QrScanExperience.model_validate(clean)

    @staticmethod
    def _row_to_qr_template(row: sqlite3.Row) -> QrTemplateRecord:
        try:
            raw_design = json.loads(str(row['design_json'] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_design = {}
        try:
            raw_experience = json.loads(str(row['experience_json'] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_experience = {}
        return QrTemplateRecord(
            id=str(row['id']), name=str(row['name']), description=str(row['description'] or ''),
            tracking_mode=str(row['tracking_mode'] or 'tracked'), identity_mode=str(row['identity_mode'] or 'anonymous'),
            design=Database._normalize_qr_design(raw_design), experience=Database._normalize_qr_experience(raw_experience),
            is_default=bool(row['is_default']), qr_count=int(row['qr_count'] or 0),
            created_at=datetime.fromisoformat(str(row['created_at'])), updated_at=datetime.fromisoformat(str(row['updated_at'])),
        )

    @staticmethod
    def _row_to_qr_code(row: sqlite3.Row) -> QrCodeRecord:
        try:
            raw_design = json.loads(str(row['design_json'] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_design = {}
        try:
            raw_experience = json.loads(str(row['experience_json'] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_experience = {}
        try:
            raw_payload = json.loads(str(row['payload_json'] or "{}")) if 'payload_json' in row.keys() else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_payload = {}
        if not isinstance(raw_payload, dict):
            raw_payload = {}
        design = Database._normalize_qr_design(raw_design)
        experience = Database._normalize_qr_experience(raw_experience)
        return QrCodeRecord(
            id=str(row['id']), name=str(row['name']), slug=str(row['slug']),
            qr_type=str(row['qr_type'] or 'url') if 'qr_type' in row.keys() else 'url',
            tracking_mode=str(row['tracking_mode'] or 'tracked') if 'tracking_mode' in row.keys() else 'tracked',
            identity_mode=str(row['identity_mode'] or 'anonymous') if 'identity_mode' in row.keys() else 'anonymous',
            target_url=str(row['target_url'] or ''), content=raw_payload,
            public_base_url=str(row['public_base_url']) if row['public_base_url'] else None,
            short_url=str(row['short_url']) if row['short_url'] else None,
            design=design, experience=experience,
            template_id=(str(row['template_id']) if 'template_id' in row.keys() and row['template_id'] else None),
            template_name=(str(row['template_name']) if 'template_name' in row.keys() and row['template_name'] else None),
            active=bool(row['active']), created_at=datetime.fromisoformat(str(row['created_at'])),
            updated_at=datetime.fromisoformat(str(row['updated_at'])), total_scans=int(row['total_scans'] or 0),
            unique_visitors=int(row['unique_visitors'] or 0), unique_emails=int(row['unique_emails'] or 0) if 'unique_emails' in row.keys() else 0,
            country_count=int(row['country_count'] or 0),
            legacy_scans=int(row['legacy_scans'] or 0) if 'legacy_scans' in row.keys() else 0,
        )

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> SheetSource:
        return SheetSource(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            spreadsheet_id=row["spreadsheet_id"],
            enabled=bool(row["enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_sync_at=datetime.fromisoformat(row["last_sync_at"])
            if row["last_sync_at"]
            else None,
            last_sync_status=row["last_sync_status"],
            last_error=row["last_error"],
        )
