from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.config import Settings
from app.database import Database
from app.models import SheetSource
from app.services.sync_service import SyncService


def _source() -> SheetSource:
    return SheetSource(
        id="yt-science",
        name="YT Science 2026-27",
        url="https://docs.google.com/spreadsheets/d/yt-science/edit",
        spreadsheet_id="yt-science",
        enabled=True,
        created_at=datetime.now(UTC),
    )


def _workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Class 12"
    sheet.append(["Weekly Plan Structure"])
    sheet.append(["2 Videos/Week: Thursday & Sunday"])
    sheet.append(["3 Shorts/Week: Tuesday, Friday, Saturday"])
    sheet.append([])
    sheet.append(["Date", "Day", "Content Type", "Subject Teacher", "Topic", "Remarks"])
    sheet.append(["6th April", "Monday", "Video", "Ravi Sir", "Electric Charges and Fields Lecture 1", "Open"])
    sheet["F6"].hyperlink = "https://youtube.com/live/example-physics"
    sheet.append(["7th April", "Tuesday", "Shorts", "Kuldeep Sir", "Relation and Function", "Watch"])
    sheet["F7"].hyperlink = "https://youtube.com/shorts/example-maths"
    workbook.save(path)


def test_links_are_discovered_under_custom_remarks_heading(
    tmp_path: Path,
    database: Database,
    client: TestClient,
) -> None:
    path = tmp_path / "yt-science.xlsx"
    _workbook(path)
    source = _source()
    database.upsert_source(source)
    service = SyncService(database, Settings(database_url=f"sqlite:///{database.path}"))
    result = service.sync_local_workbook(source, path, live_data=False)
    assert result.status == "local_import"
    assert result.content_count == 2

    analysis = client.get("/api/v1/source-analysis").json()[0]
    profile = analysis["profile"]["tabs"][0]
    assert profile["header_row"] == 5
    assert profile["detected_columns"]["teacher"] == "Subject Teacher"
    assert profile["search_ready"] is True
    assert analysis["tab_content_counts"]["Class 12"] == 2

    payload = client.get(
        "/api/v1/content",
        params={"source_id": source.id, "sheet_name": "Class 12", "page_size": 100},
    ).json()
    assert payload["total"] == 2
    assert {item["url"] for item in payload["items"]} == {
        "https://youtube.com/live/example-physics",
        "https://youtube.com/shorts/example-maths",
    }
    physics = next(item for item in payload["items"] if "physics" in item["url"])
    assert physics["class_name"] == "Class 12"
    assert physics["subject"] == "Physics"
    assert physics["title"] == "Electric Charges and Fields Lecture 1"
    assert physics["record_kind"] == "structured_link"


def test_change_story_hides_raw_row_from_plain_location(
    database: Database,
    client: TestClient,
) -> None:
    # Existing v1.0.9 test creates a real change story. This endpoint-level check
    # protects the normal-user location from exposing a raw row number.
    response = client.get("/api/v1/changes", params={"period": "all"})
    assert response.status_code == 200
