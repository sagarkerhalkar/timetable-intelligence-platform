from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app.database import Database


def test_v120_qr_scan_columns_are_migrated_before_new_indexes(tmp_path) -> None:
    database_path = tmp_path / "v119.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE qr_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_id TEXT NOT NULL,
                scanned_at TEXT NOT NULL,
                visitor_hash TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'Unknown',
                device_type TEXT NOT NULL DEFAULT 'Other',
                browser TEXT NOT NULL DEFAULT 'Other'
            );
            CREATE INDEX idx_qr_scans_qr_time ON qr_scans(qr_id, scanned_at DESC);
            CREATE INDEX idx_qr_scans_time ON qr_scans(scanned_at DESC);
            CREATE INDEX idx_qr_scans_country ON qr_scans(country);
            """
        )

    database = Database(database_path)
    with database.connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(qr_scans)").fetchall()}
        assert {
            "event_hash", "confirmed", "operating_system", "platform",
            "source_confidence", "referrer_host", "language", "screen_width", "screen_height",
        }.issubset(columns)
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(qr_scans)").fetchall()}
        assert "idx_qr_scans_platform" in indexes
        assert "idx_qr_scans_confirmed" in indexes
        assert "idx_qr_scans_event" in indexes


def test_legacy_qr_customization_is_normalized_for_listing(tmp_path) -> None:
    db = Database(tmp_path / "legacy-qr-values.db")
    now = datetime.now(UTC).isoformat()
    with db.connect() as connection:
        connection.execute(
            """INSERT INTO qr_codes(
                id,name,slug,target_url,public_base_url,short_url,design_json,experience_json,active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            (
                "legacy-values", "Legacy values", "abc2345", "https://example.com",
                "https://q.nexttoppers.workers.dev", None,
                '{"foreground_color":"#000000","dot_style":"old-shape","logo_scale_percent":99}',
                '{"mode":"brand","redirect_delay_ms":350,"logo_scale_percent":99,"image_scale_percent":10}',
                now, now,
            ),
        )
    rows = db.list_qr_codes()
    assert len(rows) == 1
    assert rows[0].design.dot_style == "rounded"
    assert rows[0].design.logo_scale_percent == 28
    assert rows[0].experience.redirect_delay_ms == 650
    assert rows[0].experience.logo_scale_percent == 55
    assert rows[0].experience.image_scale_percent == 40

