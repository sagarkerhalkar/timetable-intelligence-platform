"""QR speed + scan-safety update (Nov 2026).

These tests use a temporary database only. They check that the faster code
returns the same data and that a briefly locked database no longer loses scans.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.api import qr_fast, qr_reports, qr_scale
from app.database import Database


def _point_api_at(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    for module in (qr_scale, qr_reports, qr_fast):
        monkeypatch.setattr(module, "get_database", lambda: database)
    qr_scale._ANALYTICS_CACHE.clear()
    qr_reports._REPORT_CACHE.clear()


def _add_qr(database: Database, slug: str = "speed01") -> str:
    now = datetime.now(UTC).isoformat()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO qr_codes(id,name,slug,target_url,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (f"id-{slug}", f"QR {slug}", slug, "https://example.com", now, now),
        )
    return f"id-{slug}"


def _add_scan(database: Database, qr_id: str, n: int, *, device: str = "Mobile", confirmed: bool = True) -> None:
    database.record_qr_scan(
        qr_id=qr_id,
        scanned_at=datetime.now(UTC) - timedelta(minutes=100 - n),
        visitor_hash=f"v{n}",
        event_hash=f"e-{qr_id}-{n}-{device}-{confirmed}",
        confirmed=confirmed,
        country="India",
        device_type=device,
        browser="Chrome",
    )


def test_schema_script_runs_once_not_on_every_request(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point_api_at(monkeypatch, database)
    qr_scale._SCHEMA_READY.discard(str(database.path))
    calls = {"n": 0}
    real = qr_scale.ensure_qr_scale_schema

    def counting() -> None:
        calls["n"] += 1
        real()

    monkeypatch.setattr(qr_scale, "ensure_qr_scale_schema", counting)
    for _ in range(5):
        qr_scale.qr_scale_health()
        qr_scale.qr_scale_recent_scans(limit=25, cursor=None, qr_id="")
    assert calls["n"] == 1


def test_recent_scans_newest_first_and_only_human_confirmed(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point_api_at(monkeypatch, database)
    qr_scale.ensure_qr_scale_schema()
    qr_id = _add_qr(database)
    for n in range(30):
        _add_scan(database, qr_id, n)
    _add_scan(database, qr_id, 50, device="bot")
    _add_scan(database, qr_id, 51, confirmed=False)

    first = qr_scale.qr_scale_recent_scans(limit=25, cursor=None, qr_id="")
    ids = [item["id"] for item in first["items"]]
    assert ids == sorted(ids, reverse=True)
    assert len(ids) == 25 and first["has_more"] is True
    assert all(item["device_type"] != "bot" for item in first["items"])

    second = qr_scale.qr_scale_recent_scans(limit=25, cursor=first["next_cursor"], qr_id="")
    assert len(second["items"]) == 5 and second["has_more"] is False
    assert max(item["id"] for item in second["items"]) < min(ids)

    one_qr = qr_scale.qr_scale_recent_scans(limit=25, cursor=None, qr_id=qr_id)
    assert [item["id"] for item in one_qr["items"]] == ids


def test_recent_scans_query_does_not_sort_every_scan(database: Database) -> None:
    qr_scale._SCHEMA_READY.discard(str(database.path))
    with database.connect() as connection:
        connection.executescript(qr_scale._SCALE_SCHEMA)
        plan = " ".join(
            row[3] for row in connection.execute(
                "EXPLAIN QUERY PLAN SELECT s.id FROM qr_scans s JOIN qr_codes q ON q.id=s.qr_id "
                "WHERE +s.confirmed=1 AND +s.device_type!='bot' ORDER BY s.id DESC LIMIT 26"
            )
        )
    assert "TEMP B-TREE" not in plan


def test_analytics_cache_returns_independent_copies(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point_api_at(monkeypatch, database)
    qr_scale.ensure_qr_scale_schema()
    first = qr_scale.qr_scale_analytics(period="30d", qr_id="")
    first["verified_scans"] = -999
    second = qr_scale.qr_scale_analytics(period="30d", qr_id="")
    assert second["verified_scans"] != -999


def test_report_cache_is_shared_and_safe(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point_api_at(monkeypatch, database)
    qr_id = _add_qr(database)
    for n in range(3):
        _add_scan(database, qr_id, n)
    first = qr_reports.summary(period="30d", qr_id="")
    assert first["verified_scans"] == 3
    first["locations"].clear()
    again = qr_reports.summary(period="30d", qr_id="")
    assert again["verified_scans"] == 3 and again["locations"]


def test_busy_retry_retries_lock_errors_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qr_fast.time, "sleep", lambda _: None)
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "saved"

    assert qr_fast._with_busy_retry(flaky) == "saved"
    assert attempts["n"] == 3

    def broken() -> None:
        raise sqlite3.OperationalError("no such table: qr_scans")

    with pytest.raises(sqlite3.OperationalError):
        qr_fast._with_busy_retry(broken)


def test_scan_is_saved_after_lock_and_never_double_counted(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point_api_at(monkeypatch, database)
    _add_qr(database, "lockqr")
    monkeypatch.setattr(qr_fast.time, "sleep", lambda _: None)
    real = database.record_qr_scan
    state = {"locked_once": False}

    def locked_then_ok(**kwargs):
        if not state["locked_once"]:
            state["locked_once"] = True
            raise sqlite3.OperationalError("database is locked")
        return real(**kwargs)

    monkeypatch.setattr(database, "record_qr_scan", locked_then_ok)
    event = qr_fast.FastScanEvent(event_id="same-event", visitor_id="v1", user_agent="Mozilla/5.0 (iPhone) Mobile")
    assert qr_fast.qr_fast_confirm("lockqr", event) == {"ok": True, "recorded": True}
    assert qr_fast.qr_fast_confirm("lockqr", event) == {"ok": True, "recorded": False}
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM qr_scans").fetchone()[0] == 1


def test_qr_image_drawn_once_then_served_from_cache(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    from app.api import routes

    drawn: list[str] = []

    def fake_draw(url, design, db):
        drawn.append(url)
        return b"\x89PNG\r\n\x1a\n" + url.encode() + str(sorted(design.items())).encode()

    monkeypatch.setattr(routes, "_render_qr_png_uncached", fake_draw)
    routes._QR_IMAGE_MEMORY.clear()
    design = {"foreground_color": "#111827", "dot_style": "rounded"}

    first = routes._render_qr_png("https://q.example/q/abc", design, database)
    again = routes._render_qr_png("https://q.example/q/abc", dict(design), database)
    assert first == again and len(drawn) == 1

    # A changed design or link is a different image and is drawn fresh.
    routes._render_qr_png("https://q.example/q/abc", {**design, "dot_style": "dots"}, database)
    routes._render_qr_png("https://q.example/q/xyz", design, database)
    assert len(drawn) == 3

    # After an API restart (empty memory) the copy on disk is used.
    routes._QR_IMAGE_MEMORY.clear()
    assert routes._render_qr_png("https://q.example/q/abc", design, database) == first
    assert len(drawn) == 3


def test_qr_image_cache_notices_a_replaced_logo(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    from app.api import routes

    drawn: list[int] = []
    monkeypatch.setattr(routes, "_render_qr_png_uncached", lambda u, d, db: drawn.append(1) or b"\x89PNG\r\n\x1a\nx")
    routes._QR_IMAGE_MEMORY.clear()
    asset_id = "a" * 24
    logo = routes._qr_asset_dir(database) / f"{asset_id}.png"
    logo.write_bytes(b"one")
    design = {"logo_asset_id": asset_id}
    routes._render_qr_png("https://q.example/q/logo", design, database)
    logo.write_bytes(b"a different logo")
    routes._render_qr_png("https://q.example/q/logo", design, database)
    assert len(drawn) == 2
