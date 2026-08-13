from __future__ import annotations

from starlette.testclient import TestClient


def _template(client: TestClient, name: str, *, tracked: bool = True) -> dict[str, object]:
    response = client.post(
        "/api/v1/qr-templates",
        json={
            "name": name,
            "description": "Reusable school campaign design",
            "tracking_mode": "tracked" if tracked else "direct",
            "identity_mode": "anonymous",
            "design": {
                "foreground_color": "#173EA5",
                "background_color": "#FFFFFF",
                "dot_style": "dots",
                "marker_border_style": "circle",
                "marker_center_style": "rounded",
                "frame_style": "badge",
                "frame_text": "SCAN NOW",
                "logo_scale_percent": 20,
            },
            "experience": {
                "mode": "page",
                "title": "Opening…",
                "message": "Please wait",
                "accent_color": "#2455FF",
                "background_color": "#F8FAFC",
                "redirect_delay_ms": 900,
                "image_fit": "cover",
                "image_scale_percent": 100,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_multiple_templates_can_be_saved_duplicated_and_defaulted(client: TestClient) -> None:
    commerce = _template(client, "Commerce 2026")
    science = _template(client, "Science 2026")

    duplicate = client.post(f"/api/v1/qr-templates/{commerce['id']}/duplicate")
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["name"].startswith("Commerce 2026 Copy")

    make_default = client.patch(f"/api/v1/qr-templates/{science['id']}", json={"is_default": True})
    assert make_default.status_code == 200, make_default.text
    templates = client.get("/api/v1/qr-templates").json()
    assert len(templates) == 3
    assert sum(1 for item in templates if item["is_default"]) == 1
    assert next(item for item in templates if item["id"] == science["id"])["is_default"] is True


def test_bulk_create_reuses_one_template_and_each_qr_has_independent_analytics(client: TestClient) -> None:
    template = _template(client, "Admissions Brand")
    response = client.post(
        "/api/v1/qr-bulk",
        json={
            "template_id": template["id"],
            "items": [
                {"name": "Commerce 11th", "url": "https://example.com/commerce-11"},
                {"name": "Commerce 12th", "url": "https://example.com/commerce-12"},
                {"name": "Science 11th", "url": "https://example.com/science-11"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["count"] == 3
    created = body["created"]
    assert {item["name"] for item in created} == {"Commerce 11th", "Commerce 12th", "Science 11th"}
    assert all(item["template_id"] == template["id"] for item in created)
    assert all(item["template_name"] == "Admissions Brand" for item in created)
    assert len({item["slug"] for item in created}) == 3
    assert all(item["design"]["dot_style"] == "dots" for item in created)
    assert all(item["experience"]["mode"] == "page" for item in created)

    first, second, third = created
    first_scan = client.post(
        f"/api/v1/qr/confirm/{first['slug']}",
        headers={"user-agent": "Mozilla/5.0 Chrome/151 Mobile Safari/537.36", "cf-ipcountry": "IN"},
        json={"visitor_id": "bulk-device-first", "event_id": "bulk-event-first"},
    )
    assert first_scan.status_code == 200, first_scan.text
    second_scan_1 = client.post(
        f"/api/v1/qr/confirm/{second['slug']}",
        headers={"user-agent": "Mozilla/5.0 Chrome/151 Mobile Safari/537.36", "cf-ipcountry": "IN"},
        json={"visitor_id": "bulk-device-second", "event_id": "bulk-event-second-1"},
    )
    second_scan_2 = client.post(
        f"/api/v1/qr/confirm/{second['slug']}",
        headers={"user-agent": "Mozilla/5.0 Chrome/151 Mobile Safari/537.36", "cf-ipcountry": "IN"},
        json={"visitor_id": "bulk-device-second", "event_id": "bulk-event-second-2"},
    )
    assert second_scan_1.status_code == 200 and second_scan_2.status_code == 200

    first_stats = client.get(f"/api/v1/qr-analytics?qr_id={first['id']}").json()
    second_stats = client.get(f"/api/v1/qr-analytics?qr_id={second['id']}").json()
    third_stats = client.get(f"/api/v1/qr-analytics?qr_id={third['id']}").json()
    assert first_stats["total_scans"] == 1
    assert second_stats["total_scans"] == 2
    assert second_stats["unique_visitors"] == 1
    assert third_stats["total_scans"] == 0


def test_direct_template_is_not_allowed_for_bulk_analytics(client: TestClient) -> None:
    template = _template(client, "Direct Print", tracked=False)
    response = client.post(
        "/api/v1/qr-bulk",
        json={"template_id": template["id"], "items": [{"name": "One", "url": "https://example.com/one"}]},
    )
    assert response.status_code == 422
    assert "Tracked template" in response.text


def test_deleting_template_keeps_already_created_qr_codes(client: TestClient) -> None:
    template = _template(client, "Keep Existing")
    created = client.post(
        "/api/v1/qr-bulk",
        json={"template_id": template["id"], "items": [{"name": "Persistent", "url": "https://example.com/persistent"}]},
    ).json()["created"][0]

    deleted = client.delete(f"/api/v1/qr-templates/{template['id']}")
    assert deleted.status_code == 204
    code = client.get(f"/api/v1/qr-codes/{created['id']}")
    assert code.status_code == 200
    assert code.json()["template_id"] is None
    assert code.json()["target_url"] == "https://example.com/persistent"
