from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.database import Database
from app.models import NotificationRule, SheetSource


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_list_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "name": "Science",
            "url": "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0",
            "enabled": True,
        },
    )
    assert response.status_code == 201
    source = response.json()
    assert source["spreadsheet_id"] == "abc123"
    listed = client.get("/api/v1/sources").json()
    assert listed[0]["id"] == source["id"]


def test_invalid_source_url(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={"name": "Bad source", "url": "https://example.com/no-sheet", "enabled": True},
    )
    assert response.status_code == 422


def test_pagination_empty(client: TestClient) -> None:
    response = client.get("/api/v1/timetable?page=1&page_size=20")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 1}


def test_notification_rule_roundtrip(client: TestClient) -> None:
    payload = {
        "id": "rule-1",
        "name": "Thirty minute reminder",
        "enabled": True,
        "event_type": "before_class",
        "minutes_before": 30,
        "channels": ["push", "email", "push"],
        "recipients": ["teacher@example.com"],
        "streams": ["Commerce"],
        "classes": ["Class 12"],
        "subjects": [],
        "include_pdf": True,
        "include_excel": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    response = client.post("/api/v1/notification-rules", json=payload)
    assert response.status_code == 201
    assert response.json()["channels"] == ["email", "push"]
    listed = client.get("/api/v1/notification-rules").json()
    assert listed[0]["id"] == "rule-1"


def test_dashboard(database: Database, client: TestClient) -> None:
    source = SheetSource(
        id="source-1",
        name="Test",
        url="https://docs.google.com/spreadsheets/d/abc/edit",
        spreadsheet_id="abc",
        enabled=True,
        created_at=datetime.now(UTC),
    )
    database.upsert_source(source)
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert response.json()["connected_sources"] == 1
    assert response.json()["tabs_scanned"] == 0


def test_notification_schedule_and_test_history(client: TestClient) -> None:
    payload = {
        "id": "daily-rule",
        "name": "Morning timetable",
        "enabled": True,
        "event_type": "daily_timetable",
        "send_time": "07:15",
        "weekday": None,
        "minutes_before": None,
        "timezone": "Asia/Kolkata",
        "channels": ["email"],
        "recipients": ["teacher@example.com"],
        "streams": [],
        "classes": [],
        "subjects": [],
        "include_pdf": False,
        "include_excel": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    saved = client.post("/api/v1/notification-rules", json=payload)
    assert saved.status_code == 201
    assert saved.json()["send_time"] == "07:15"

    status = client.get("/api/v1/notification-status")
    assert status.status_code == 200
    assert status.json()["scheduler_active"] is True
    assert status.json()["sheet_refresh_minutes"] == 30

    tested = client.post("/api/v1/notification-rules/daily-rule/test")
    assert tested.status_code == 200
    assert tested.json()["scheduler_ok"] is True
    assert tested.json()["deliveries"][0]["status"] == "not_configured"

    history = client.get("/api/v1/notification-deliveries")
    assert history.status_code == 200
    assert history.json()[0]["rule_id"] == "daily-rule"


def test_notification_rule_can_be_deleted_with_history(client: TestClient) -> None:
    payload = {
        "id": "delete-me",
        "name": "Delete this rule",
        "enabled": True,
        "event_type": "daily_timetable",
        "send_time": "07:00",
        "weekday": None,
        "minutes_before": None,
        "timezone": "Asia/Kolkata",
        "channels": ["email"],
        "recipients": ["teacher@example.com"],
        "streams": [],
        "classes": [],
        "subjects": [],
        "include_pdf": False,
        "include_excel": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    assert client.post("/api/v1/notification-rules", json=payload).status_code == 201
    assert client.post("/api/v1/notification-rules/delete-me/test").status_code == 200
    assert client.get("/api/v1/notification-deliveries").json()

    deleted = client.delete("/api/v1/notification-rules/delete-me")
    assert deleted.status_code == 204
    assert client.get("/api/v1/notification-rules").json() == []
    assert client.get("/api/v1/notification-deliveries").json() == []
    assert client.delete("/api/v1/notification-rules/delete-me").status_code == 404


def test_personal_whatsapp_needs_no_business_api_and_requires_final_send_tap(client: TestClient) -> None:
    payload = {
        "id": "personal-wa",
        "name": "Personal WhatsApp test",
        "enabled": True,
        "event_type": "daily_timetable",
        "send_time": "07:00",
        "weekday": None,
        "minutes_before": None,
        "timezone": "Asia/Kolkata",
        "channels": ["whatsapp_personal"],
        "recipients": ["+919876543210"],
        "streams": ["Nirmaan"],
        "classes": ["Class 8"],
        "subjects": [],
        "include_pdf": False,
        "include_excel": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    assert client.post("/api/v1/notification-rules", json=payload).status_code == 201
    status = client.get("/api/v1/notification-status").json()
    assert status["configured_channels"]["whatsapp_personal"] is True

    tested = client.post("/api/v1/notification-rules/personal-wa/test")
    assert tested.status_code == 200
    delivery = tested.json()["deliveries"][0]
    assert delivery["channel"] == "whatsapp_personal"
    assert delivery["status"] == "action_required"
    assert delivery["error"] is None
