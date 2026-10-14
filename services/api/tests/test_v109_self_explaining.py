from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.config import Settings
from app.database import Database
from app.models import CellSnapshot, NotificationRule, SheetSource
from app.services.change_detector import detect_cell_changes
from app.services.sync_service import SyncService


def _source(source_id: str = "new-sheet", name: str = "New Learning Sheet") -> SheetSource:
    return SheetSource(
        id=source_id,
        name=name,
        url=f"https://docs.google.com/spreadsheets/d/{source_id}/edit",
        spreadsheet_id=source_id,
        enabled=True,
        created_at=datetime.now(UTC),
    )


def _new_sheet_workbook(path: Path) -> None:
    workbook = Workbook()
    ready = workbook.active
    ready.title = "Hindi Library"
    ready.append(["Course Name", "Class", "Subject", "Chapter Name", "Made by", "PDF Link", "App Status"])
    ready.append(["Nirmaan", "Class 8", "Hindi", "कबीर के दोहे", "Kavita", "Kabir lesson.pdf", "Done"])
    ready["F2"].hyperlink = "https://example.com/kabir.pdf"
    unclear = workbook.create_sheet("Unclear Notes")
    unclear.append(["Thing", "Other"])
    unclear.append(["abc", "def"])
    workbook.save(path)


def test_new_sheet_is_profiled_indexed_and_explains_missing_headings(
    tmp_path: Path,
    database: Database,
    client: TestClient,
) -> None:
    path = tmp_path / "new-sheet.xlsx"
    _new_sheet_workbook(path)
    source = _source()
    database.upsert_source(source)
    service = SyncService(database, Settings(database_url=f"sqlite:///{database.path}"))
    result = service.sync_local_workbook(source, path, live_data=False)
    assert result.status == "local_import"

    analysis = client.get("/api/v1/source-analysis").json()[0]
    assert analysis["search_ready_tabs"] >= 1
    assert analysis["needs_setup_tabs"] >= 1
    profiles = {item["name"]: item for item in analysis["profile"]["tabs"]}
    assert profiles["Hindi Library"]["search_ready"] is True
    assert profiles["Hindi Library"]["detected_columns"]["topic"] == "Chapter Name"
    assert profiles["Unclear Notes"]["search_ready"] is False
    assert profiles["Unclear Notes"]["missing_recommended_fields"]

    search = client.get(
        "/api/v1/content",
        params={"query": "kabir", "source_id": source.id, "sheet_name": "Hindi Library"},
    )
    assert search.status_code == 200
    payload = search.json()
    assert payload["total"] == 1
    assert payload["items"][0]["topic"] == "कबीर के दोहे"
    assert payload["items"][0]["url"] == "https://example.com/kabir.pdf"


def test_remove_sheet_deletes_only_local_index_and_cleans_rule_source(
    database: Database,
    client: TestClient,
) -> None:
    source = _source("remove-me", "Remove Me")
    database.upsert_source(source)
    rule = NotificationRule(
        id="rule-remove",
        name="Rule",
        event_type="daily_timetable",
        source_ids=[source.id],
        channels=["whatsapp_personal"],
        recipients=["+919999999999"],
        created_at=datetime.now(UTC),
    )
    database.upsert_notification_rule(rule)
    response = client.delete(f"/api/v1/sources/{source.id}")
    assert response.status_code == 204
    assert database.get_source(source.id) is None
    assert database.get_notification_rule(rule.id).source_ids == []


def test_change_history_names_fields_and_row_in_plain_language(
    database: Database,
    client: TestClient,
) -> None:
    source = _source("history", "Test History")
    database.upsert_source(source)
    common = dict(source_id=source.id, workbook_name=source.name, sheet_name="PRARAMBH 2026")
    previous = [
        CellSnapshot(**common, coordinate="A1", row=1, column=1, value="Class", style_key=""),
        CellSnapshot(**common, coordinate="B1", row=1, column=2, value="Subject", style_key=""),
        CellSnapshot(**common, coordinate="C1", row=1, column=3, value="Chapter Name", style_key=""),
        CellSnapshot(**common, coordinate="D1", row=1, column=4, value="App Status", style_key=""),
        CellSnapshot(**common, coordinate="A2", row=2, column=1, value="Class 11", style_key=""),
        CellSnapshot(**common, coordinate="B2", row=2, column=2, value="Political Science", style_key=""),
        CellSnapshot(**common, coordinate="C2", row=2, column=3, value="Election and Representation", style_key=""),
        CellSnapshot(**common, coordinate="D2", row=2, column=4, value="Pending", style_key=""),
    ]
    current = [cell.model_copy() for cell in previous]
    current[-1] = current[-1].model_copy(update={"value": "Done"})
    changes = detect_cell_changes(previous, current)
    assert len(changes) == 1
    assert changes[0].field_name == "App Status"
    assert "Political Science" in (changes[0].row_label or "")
    database.insert_changes(changes)

    response = client.get(
        "/api/v1/changes",
        params={"period": "all", "source_id": source.id, "sheet_name": "PRARAMBH 2026"},
    )
    story = response.json()["items"][0]
    assert story["summary"].casefold().startswith("app status changed from")
    assert "row" not in story["plain_location"].casefold()
    assert story["details"][0]["field_name"] == "App Status"
    assert story["details"][0]["old_value"] == "Pending"
    assert story["details"][0]["new_value"] == "Done"
    summary = client.get(
        "/api/v1/changes/summary",
        params={"period": "all", "source_id": source.id, "sheet_name": "PRARAMBH 2026"},
    ).json()
    assert summary == {"added": 0, "updated": 1, "deleted": 0, "total": 1, "sources_checked": 1}
