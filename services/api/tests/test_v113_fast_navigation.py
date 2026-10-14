from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.database import Database
from app.models import SheetSource, TestRecord


TEST_SERIES_SHEET_ID = "1ZYbITcTnAAbrLOyQ3pzaykEAmOt9Q1EH6gkImY33JXQ"


def _source() -> SheetSource:
    return SheetSource(
        id="test-nav-source",
        name="Test Series - 2026",
        url=f"https://docs.google.com/spreadsheets/d/{TEST_SERIES_SHEET_ID}/edit",
        spreadsheet_id=TEST_SERIES_SHEET_ID,
        enabled=True,
        created_at=datetime.now(UTC),
    )


def _record(record_id: str, sheet_name: str, row: int) -> TestRecord:
    return TestRecord(
        id=record_id,
        source_id="test-nav-source",
        workbook_name="Test Series - 2026",
        sheet_name=sheet_name,
        source_row=row,
        class_name="Class 12",
        subject="Physics",
        topic=f"Test {row}",
        app_status="Pending",
        test_date_status="07-08-2026",
        fingerprint=f"fingerprint-{record_id}",
    )


def test_test_tab_counts_use_compact_database_aggregation(database: Database) -> None:
    source = _source()
    database.upsert_source(source)
    database.replace_test_records(
        source.id,
        [
            _record("p1", "PRARAMBH 2026", 2),
            _record("p2", "PRARAMBH 2026", 3),
            _record("n1", "Nirman 2026", 2),
        ],
    )

    assert database.test_sheet_counts(source.id) == {
        "PRARAMBH 2026": 2,
        "Nirman 2026": 1,
    }
    filtered = database.list_test_records(source_id=source.id, sheet_names=["Nirman 2026"])
    assert [item.id for item in filtered] == ["n1"]


def test_test_tab_counts_endpoint_is_lightweight(database: Database, client: TestClient) -> None:
    source = _source()
    database.upsert_source(source)
    database.replace_test_records(
        source.id,
        [
            _record("p1", "PRARAMBH 2026", 2),
            _record("n1", "Nirman 2026", 2),
        ],
    )

    response = client.get("/api/v1/test-monitor/tabs")
    assert response.status_code == 200
    assert response.json() == {"Nirman 2026": 1, "PRARAMBH 2026": 1}

    filtered = client.get("/api/v1/test-monitor", params={"sheet_name": "Nirman 2026"})
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["summary"]["total_tests"] == 1
    assert payload["summary"]["sheet_counts"] == {"Nirman 2026": 1}
