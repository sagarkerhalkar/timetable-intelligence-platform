from __future__ import annotations

from datetime import UTC, date, datetime, time

from fastapi.testclient import TestClient

from app.database import Database
from app.models import (
    ChangeRecord,
    ChangeType,
    ContentItem,
    ContentType,
    NotificationRule,
    SheetSource,
    TimetableEntry,
)
from app.services.notifications import build_notification_message
from app.utils import devanagari_to_latin, normalize_search_text, stable_hash


def _source(source_id: str, name: str) -> SheetSource:
    return SheetSource(
        id=source_id,
        name=name,
        url=f"https://docs.google.com/spreadsheets/d/{source_id}/edit",
        spreadsheet_id=source_id,
        enabled=True,
        created_at=datetime.now(UTC),
    )


def _content(source_id: str, title: str, topic: str, sheet: str) -> ContentItem:
    return ContentItem(
        id=stable_hash("content", source_id, sheet, title),
        source_id=source_id,
        workbook_name="Test Series - 2026" if source_id == "tests" else "Other Sheet",
        sheet_name=sheet,
        coordinate="K20",
        source_row=20,
        url=f"https://example.com/{source_id}/{stable_hash(title)}.docx",
        title=title,
        content_type=ContentType.DOCUMENT,
        stream="Nirmaan",
        class_name="Class 8",
        batch="Nirmaan",
        subject="Hindi",
        topic=topic,
        teacher="Kavita",
        search_text=f"{title} {topic} Hindi Class 8",
        confidence=0.99,
        fingerprint=stable_hash(source_id, title),
    )


def test_devanagari_transliteration_supports_normal_english_spelling() -> None:
    assert devanagari_to_latin("कबीर") == "kabir"
    normalized = normalize_search_text("कबीर के दोहे")
    assert "कबीर" in normalized
    assert "kabir ke dohe" in normalized
    assert "sanskrit" in normalize_search_text("संस्कृत")


def test_search_can_filter_by_google_sheet_and_tab(
    database: Database,
    client: TestClient,
) -> None:
    database.upsert_source(_source("tests", "Test Series - 2026"))
    database.upsert_source(_source("other", "Other Sheet"))
    database.replace_content(
        "tests",
        [_content("tests", "Class VIII Hindi कबीर के दोहे", "कबीर के दोहे", "Nirman 2026")],
    )
    database.replace_content(
        "other",
        [_content("other", "Unrelated English lesson", "Grammar", "English")],
    )

    response = client.get("/api/v1/content", params={"query": "kabir", "source_id": "tests"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["topic"] == "कबीर के दोहे"

    wrong_source = client.get("/api/v1/content", params={"query": "kabir", "source_id": "other"})
    assert wrong_source.status_code == 200
    assert wrong_source.json()["total"] == 0

    wrong_tab = client.get(
        "/api/v1/content",
        params={"query": "kabir", "source_id": "tests", "sheet_name": "CUET 2026"},
    )
    assert wrong_tab.json()["total"] == 0


def test_notification_message_contains_full_human_path(database: Database) -> None:
    database.upsert_source(_source("humanities", "Humanities"))
    entry = TimetableEntry(
        id="entry-1",
        source_id="humanities",
        workbook_name="Humanities",
        sheet_name="Weekly Planner",
        source_row=12,
        source_coordinates=["A12", "B12"],
        class_date=date.today(),
        day="Thursday",
        start_time=time(17, 0),
        stream="Humanities",
        class_name="Class 11",
        batch="Prarambh",
        subject="Political Science",
        topic="Election and Representation (L3) - Pol.Science",
        confidence=1,
        fingerprint="fp-1",
    )
    database.replace_timetable("humanities", [entry])
    rule = NotificationRule(
        id="rule",
        name="Daily timetable",
        event_type="daily_timetable",
        channels=["whatsapp_personal"],
        recipients=["+919999999999"],
        created_at=datetime.now(UTC),
    )
    message = build_notification_message(database, rule, target_date=date.today())
    assert "Humanities → Class 11 → Prarambh → Political Science" in message
    assert "Election and Representation (L3) - Pol.Science" in message


def test_sheet_updates_group_same_row_into_one_plain_story(
    database: Database,
    client: TestClient,
) -> None:
    database.upsert_source(_source("tests", "Test Series - 2026"))
    stamp = datetime.now(UTC)
    database.insert_changes([
        ChangeRecord(
            id="c1",
            source_id="tests",
            workbook_name="Test Series - 2026",
            sheet_name="CUET 2026",
            coordinate="B18",
            change_type=ChangeType.UPDATED,
            old_value="Political Science",
            new_value="Political Science",
            detected_at=stamp,
        ),
        ChangeRecord(
            id="c2",
            source_id="tests",
            workbook_name="Test Series - 2026",
            sheet_name="CUET 2026",
            coordinate="E18",
            change_type=ChangeType.ADDED,
            old_value=None,
            new_value="CUET QUESTION - Political Science Paper 2.docx",
            detected_at=stamp,
        ),
    ])
    response = client.get("/api/v1/changes", params={"period": "all"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    story = body["items"][0]
    assert story["category"] == "Test series"
    assert "test file added" in story["summary"].casefold()
    assert story["plain_location"] == "Test Series - 2026 → CUET 2026"
