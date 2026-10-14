from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from openpyxl import Workbook

from app.config import Settings
from app.database import Database
from app.models import SheetSource, TestRecord as RecordModel
from app.services import sync_service as sync_module
from app.services.sync_service import SyncService
from app.services.test_series import assigned_test_sunday, tests_for_sunday as select_tests_for_sunday, weekly_cycle
from app.timezones import INDIA_TIMEZONE


def _source() -> SheetSource:
    return SheetSource(
        id="test-series",
        name="Test Series - 2026",
        url="https://docs.google.com/spreadsheets/d/test/edit",
        spreadsheet_id="test",
        enabled=True,
        created_at=datetime.now(UTC),
    )


def _workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "PRARAMBH 2026"
    sheet.append([
        "Dates", "Course", "Class", "Subject", "Chapter Number", "Chapter Name",
        "Docs Link", "App Status", "Test Date", "Result Dashboard", "Video Solution Update",
    ])
    sheet.append([
        date(2026, 8, 3), "Prarambh", "Class 12", "Physics", "1", "Electric Charges",
        "Electric Charges Test.docx", "Pending", "09-08-2026", "", "",
    ])
    sheet["G2"].hyperlink = "https://docs.google.com/document/d/test/edit"
    workbook.save(path)


def _record(first_seen: datetime, *, test_date: str | None = None) -> RecordModel:
    return RecordModel(
        id=str(first_seen.timestamp()),
        source_id="test-series",
        workbook_name="Test Series - 2026",
        sheet_name="PRARAMBH 2026",
        source_row=2,
        subject="Physics",
        topic="Electric Charges",
        app_status="Pending",
        test_date_status=test_date,
        fingerprint="f",
        first_seen_at=first_seen.astimezone(UTC),
        last_seen_at=first_seen.astimezone(UTC),
    )


def test_test_workbook_does_not_open_generic_parser_third_time(
    tmp_path: Path, database: Database, monkeypatch
) -> None:
    path = tmp_path / "tests.xlsx"
    _workbook(path)
    source = _source()
    database.upsert_source(source)

    def fail_generic(*args, **kwargs):
        raise AssertionError("generic structured parser must not run after test records were found")

    monkeypatch.setattr(sync_module, "parse_structured_content_workbook", fail_generic)
    result = SyncService(database, Settings(database_url=f"sqlite:///{database.path}")).sync_local_workbook(
        source, path, live_data=False
    )
    assert result.test_record_count == 1
    assert result.content_count >= 1


def test_weekly_cycle_uses_monday_9_to_saturday_6_window() -> None:
    monday_at_9 = datetime(2026, 8, 3, 9, 0, tzinfo=INDIA_TIMEZONE)
    saturday_at_6 = datetime(2026, 8, 8, 18, 0, tzinfo=INDIA_TIMEZONE)
    saturday_late = datetime(2026, 8, 8, 18, 1, tzinfo=INDIA_TIMEZONE)
    sunday = date(2026, 8, 9)
    assert assigned_test_sunday(_record(monday_at_9)) == sunday
    assert assigned_test_sunday(_record(saturday_at_6)) == sunday
    assert assigned_test_sunday(_record(saturday_late)) is None


def test_explicit_test_date_overrides_upload_window() -> None:
    outside_window = datetime(2026, 8, 9, 20, 0, tzinfo=INDIA_TIMEZONE)
    record = _record(outside_window, test_date="16-08-2026")
    assert assigned_test_sunday(record) == date(2026, 8, 16)


def test_weekly_cycle_deadlines_are_monday_and_tuesday_6pm() -> None:
    now = datetime(2026, 8, 6, 19, 30, tzinfo=INDIA_TIMEZONE)
    start, end, sunday, result_deadline, video_deadline = weekly_cycle(now)
    assert start == datetime(2026, 8, 3, 9, 0, tzinfo=INDIA_TIMEZONE)
    assert end == datetime(2026, 8, 8, 18, 0, tzinfo=INDIA_TIMEZONE)
    assert sunday == date(2026, 8, 9)
    assert result_deadline == datetime(2026, 8, 10, 18, 0, tzinfo=INDIA_TIMEZONE)
    assert video_deadline == datetime(2026, 8, 11, 18, 0, tzinfo=INDIA_TIMEZONE)


def test_tests_for_sunday_filters_exact_cycle() -> None:
    records = [
        _record(datetime(2026, 8, 3, 9, 0, tzinfo=INDIA_TIMEZONE)),
        _record(datetime(2026, 8, 10, 9, 0, tzinfo=INDIA_TIMEZONE)),
    ]
    assert len(select_tests_for_sunday(records, date(2026, 8, 9))) == 1


def test_reset_interrupted_sync_keeps_old_data(database: Database) -> None:
    source = _source().model_copy(update={"last_sync_status": "analyzing"})
    database.upsert_source(source)
    database.reset_interrupted_syncs()
    stored = database.get_source(source.id)
    assert stored is not None
    assert stored.last_sync_status == "interrupted"
    assert "Old local data" in (stored.last_error or "")
