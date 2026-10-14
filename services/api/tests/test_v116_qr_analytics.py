from __future__ import annotations

from io import BytesIO

from starlette.testclient import TestClient


PUBLIC_QR_BASE = "https://q.nexttoppers.workers.dev"


def create_code(client: TestClient, target_url: str = "https://forms.gle/AbCdEf123456", **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"target_url": target_url, "name": "Class 12 Admission Form"}
    payload.update(extra)
    response = client.post("/api/v1/qr-codes", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def confirm_scan(
    client: TestClient,
    slug: str,
    *,
    visitor: str,
    event: str,
    country: str = "IN",
    user_agent: str = "Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36",
    source_tag: str | None = None,
    referrer: str | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/qr/confirm/{slug}",
        headers={"cf-ipcountry": country, "user-agent": user_agent, "x-forwarded-proto": "https"},
        json={
            "visitor_id": visitor,
            "event_id": event,
            "source_tag": source_tag,
            "referrer": referrer,
            "language": "en-IN",
            "timezone": "Asia/Kolkata",
            "screen_width": 1080,
            "screen_height": 2400,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_qr_accepts_any_http_link_and_uses_fixed_public_domain(client: TestClient) -> None:
    response = client.post("/api/v1/qr-codes", json={"target_url": "https://example.com/registration"})
    assert response.status_code == 201, response.text
    code = response.json()
    assert code["target_url"].startswith("https://example.com/registration")
    assert code["public_base_url"] == PUBLIC_QR_BASE
    assert code["active"] is True
    assert code["name"]


def test_verified_scans_count_total_and_unique_browser_correctly(client: TestClient) -> None:
    code = create_code(client)
    slug = str(code["slug"])

    first = confirm_scan(client, slug, visitor="browser-person-0001", event="event-confirm-0001")
    second = confirm_scan(client, slug, visitor="browser-person-0001", event="event-confirm-0002")
    assert first["recorded"] is True
    assert second["recorded"] is True

    analytics = client.get("/api/v1/qr-analytics").json()
    assert analytics["total_scans"] == 2
    assert analytics["unique_visitors"] == 1
    assert analytics["countries"]["IN"] == 2
    assert analytics["devices"]["Mobile"] == 2
    assert analytics["browsers"]["Chrome"] == 2
    assert analytics["operating_systems"]["Android"] == 2
    assert analytics["scans_30days"] == 2
    assert len(analytics["recent_scans"]) == 2


def test_duplicate_confirmation_event_does_not_double_count(client: TestClient) -> None:
    code = create_code(client)
    slug = str(code["slug"])
    first = confirm_scan(client, slug, visitor="visitor-dedupe-001", event="same-event-0001")
    second = confirm_scan(client, slug, visitor="visitor-dedupe-001", event="same-event-0001")
    assert first["recorded"] is True
    assert second["recorded"] is False
    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics["total_scans"] == 1
    assert analytics["unique_visitors"] == 1


def test_server_preview_and_old_direct_redirect_are_legacy_not_verified(client: TestClient) -> None:
    code = create_code(client)
    slug = str(code["slug"])

    resolve = client.get(f"/api/v1/qr/resolve/{slug}")
    assert resolve.status_code == 200
    analytics_before = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics_before["total_scans"] == 0
    assert analytics_before["legacy_scans"] == 0

    direct = client.get(
        f"/api/v1/qr/scan/{slug}",
        headers={"user-agent": "facebookexternalhit/1.1"},
        follow_redirects=False,
    )
    assert direct.status_code == 302
    analytics_after = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics_after["total_scans"] == 0
    assert analytics_after["legacy_scans"] == 1


def test_confirmed_bot_is_filtered_from_people_totals(client: TestClient) -> None:
    code = create_code(client)
    confirm_scan(
        client,
        str(code["slug"]),
        visitor="preview-bot-0001",
        event="preview-event-0001",
        country="US",
        user_agent="facebookexternalhit/1.1",
    )
    analytics = client.get("/api/v1/qr-analytics").json()
    assert analytics["total_scans"] == 0
    assert analytics["unique_visitors"] == 0
    assert analytics["bot_scans"] == 1


def test_tagged_source_platform_is_exact_and_untagged_web_is_detected(client: TestClient) -> None:
    code = create_code(client)
    slug = str(code["slug"])
    tagged = confirm_scan(
        client,
        slug,
        visitor="source-user-0001",
        event="source-event-0001",
        source_tag="whatsapp",
    )
    assert tagged["platform"] == "WhatsApp"
    assert tagged["source_confidence"] == "tagged"

    detected = confirm_scan(
        client,
        slug,
        visitor="source-user-0002",
        event="source-event-0002",
        referrer="https://www.instagram.com/direct/inbox/",
        user_agent="Mozilla/5.0 Instagram 365.0 Android",
    )
    assert detected["platform"] == "Instagram"
    assert detected["source_confidence"] == "detected"

    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics["platforms"]["WhatsApp"] == 1
    assert analytics["platforms"]["Instagram"] == 1
    assert analytics["attribution_confidence"]["tagged"] == 1
    assert analytics["attribution_confidence"]["detected"] == 1


def test_qr_downloads_png_svg_pdf_source_tag_and_csv(client: TestClient) -> None:
    code = create_code(client)
    qr_id = str(code["id"])
    slug = str(code["slug"])
    confirm_scan(client, slug, visitor="download-user-0001", event="download-event-0001", country="GB", source_tag="telegram")

    png = client.get(f"/api/v1/qr-codes/{qr_id}/image?format=png&download=true&source=whatsapp")
    assert png.status_code == 200
    assert png.headers["content-type"] == "image/png"
    assert png.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "attachment" in png.headers.get("content-disposition", "")

    svg = client.get(f"/api/v1/qr-codes/{qr_id}/image?format=svg&download=true&source=instagram")
    assert svg.status_code == 200
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in svg.content[:500]

    pdf = client.get(f"/api/v1/qr-codes/{qr_id}/image?format=pdf&download=true")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    export = client.get(f"/api/v1/qr-scans/export.csv?qr_id={qr_id}")
    assert export.status_code == 200
    assert "Class 12 Admission Form" in export.text
    assert "Verified" in export.text
    assert "Telegram" in export.text
    assert "Android" in export.text


def test_qr_activation_can_be_changed_without_losing_verified_history(client: TestClient) -> None:
    code = create_code(client)
    qr_id = str(code["id"])
    slug = str(code["slug"])
    confirm_scan(client, slug, visitor="status-user-0001", event="status-event-0001")

    disabled = client.post(f"/api/v1/qr-codes/{qr_id}/active?active=false")
    assert disabled.status_code == 200
    assert disabled.json()["active"] is False
    assert client.get(f"/api/v1/qr/resolve/{slug}").status_code == 410

    analytics = client.get(f"/api/v1/qr-analytics?qr_id={qr_id}").json()
    assert analytics["total_scans"] == 1

    enabled = client.post(f"/api/v1/qr-codes/{qr_id}/active?active=true")
    assert enabled.status_code == 200
    assert enabled.json()["active"] is True
    assert client.get(f"/api/v1/qr/resolve/{slug}").status_code == 200


def test_qr_scan_data_can_be_cleared_without_deleting_qr(client: TestClient) -> None:
    code = create_code(client)
    qr_id = str(code["id"])
    slug = str(code["slug"])
    confirm_scan(client, slug, visitor="clear-user-0001", event="clear-event-0001")
    confirm_scan(client, slug, visitor="clear-user-0001", event="clear-event-0002")

    cleared = client.delete(f"/api/v1/qr-codes/{qr_id}/scans")
    assert cleared.status_code == 200
    assert cleared.json()["deleted_scans"] == 2
    analytics = client.get(f"/api/v1/qr-analytics?qr_id={qr_id}").json()
    assert analytics["total_scans"] == 0
    assert client.get(f"/api/v1/qr-codes").json()[0]["id"] == qr_id


def test_qr_can_be_permanently_deleted_with_history(client: TestClient) -> None:
    code = create_code(client)
    qr_id = str(code["id"])
    slug = str(code["slug"])
    confirm_scan(client, slug, visitor="delete-user-0001", event="delete-event-0001")

    deleted = client.delete(f"/api/v1/qr-codes/{qr_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/qr/resolve/{slug}").status_code == 404
    assert all(item["id"] != qr_id for item in client.get("/api/v1/qr-codes").json())


def test_qr_uses_compact_seven_character_slug(client: TestClient) -> None:
    code = create_code(client)
    slug = str(code["slug"])
    assert len(slug) == 7
    assert all(char in "23456789abcdefghjkmnpqrstuvwxyz" for char in slug)
    assert code.get("short_url") is None


def test_advanced_qr_design_and_scan_screen_settings_roundtrip(client: TestClient) -> None:
    from PIL import Image

    logo = Image.new("RGB", (500, 500), "navy")
    raw = BytesIO()
    logo.save(raw, format="PNG")
    upload = client.post("/api/v1/qr-assets", files={"file": ("logo.png", raw.getvalue(), "image/png")})
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]

    created = client.post(
        "/api/v1/qr-codes",
        json={
            "target_url": "https://example.com/first",
            "name": "Commercial QR",
            "design": {
                "foreground_color": "#173EA5",
                "background_color": "#FFFFFF",
                "dot_style": "dots",
                "marker_border_style": "circle",
                "marker_center_style": "rounded",
                "marker_border_color": "#173EA5",
                "marker_center_color": "#E11D48",
                "frame_style": "badge",
                "frame_text": "SCAN TO JOIN",
                "logo_asset_id": asset_id,
                "logo_scale_percent": 22,
                "logo_background": True,
            },
            "experience": {
                "mode": "logo",
                "asset_id": asset_id,
                "title": "Welcome",
                "message": "Opening registration…",
                "accent_color": "#2455FF",
                "background_color": "#F8FAFC",
                "redirect_delay_ms": 900,
                "logo_scale_percent": 34,
                "image_fit": "contain",
                "image_scale_percent": 86,
            },
        },
    )
    assert created.status_code == 201, created.text
    code = created.json()
    assert code["design"]["dot_style"] == "dots"
    assert code["design"]["marker_border_style"] == "circle"
    assert code["design"]["marker_center_style"] == "rounded"
    assert code["design"]["marker_border_color"] == "#173EA5"
    assert code["design"]["marker_center_color"] == "#E11D48"
    assert code["design"]["logo_scale_percent"] == 22
    assert code["experience"]["logo_scale_percent"] == 34
    assert code["experience"]["image_scale_percent"] == 86

    rendered = client.get(f"/api/v1/qr-codes/{code['id']}/image?format=png")
    assert rendered.status_code == 200
    assert rendered.content.startswith(b"\x89PNG\r\n\x1a\n")
    vector = client.get(f"/api/v1/qr-codes/{code['id']}/image?format=svg")
    assert vector.status_code == 200
    assert b"data:image/png;base64" in vector.content

    changed = client.patch(
        f"/api/v1/qr-codes/{code['id']}",
        json={
            "target_url": "https://example.com/updated",
            "experience": {
                "mode": "page",
                "asset_id": asset_id,
                "title": "Opening your link",
                "message": "Please wait a moment…",
                "accent_color": "#7C3AED",
                "background_color": "#101828",
                "redirect_delay_ms": 1200,
                "logo_scale_percent": 28,
                "image_fit": "cover",
            },
        },
    )
    assert changed.status_code == 200, changed.text
    updated = changed.json()
    assert updated["slug"] == code["slug"]
    assert updated["target_url"] == "https://example.com/updated"
    assert updated["experience"]["mode"] == "page"


def test_qr_asset_rejects_non_image(client: TestClient) -> None:
    response = client.post("/api/v1/qr-assets", files={"file": ("bad.txt", b"not an image", "text/plain")})
    assert response.status_code == 422



def test_all_custom_marker_and_dot_styles_render(client: TestClient) -> None:
    code = create_code(client, target_url="https://example.com/style-matrix")
    qr_id = str(code["id"])
    for dots in ("square", "rounded", "dots"):
        for border in ("square", "rounded", "circle"):
            for center in ("square", "rounded", "circle"):
                changed = client.patch(
                    f"/api/v1/qr-codes/{qr_id}",
                    json={
                        "design": {
                            "foreground_color": "#111827",
                            "background_color": "#FFFFFF",
                            "dot_style": dots,
                            "marker_border_style": border,
                            "marker_center_style": center,
                            "marker_border_color": "#1D4ED8",
                            "marker_center_color": "#DC2626",
                            "frame_style": "text",
                            "frame_text": "SCAN ME",
                            "logo_asset_id": None,
                            "logo_scale_percent": 18,
                            "logo_background": True,
                        }
                    },
                )
                assert changed.status_code == 200, changed.text
                image = client.get(f"/api/v1/qr-codes/{qr_id}/image?format=png")
                assert image.status_code == 200
                assert image.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_anonymous_viewport_is_returned_as_numeric_fields(client: TestClient) -> None:
    code = create_code(client)
    response = client.post(
        f"/api/v1/qr/confirm/{code['slug']}",
        json={
            "visitor_id": "viewport-browser-0001",
            "event_id": "viewport-event-0001",
            "telemetry": {"viewport_width": 393, "viewport_height": 873},
        },
        headers={"user-agent": "Mozilla/5.0 Chrome/140"},
    )
    assert response.status_code == 200, response.text
    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics["top_devices"][0]["viewport_width"] == 393
    assert analytics["top_devices"][0]["viewport_height"] == 873
    assert analytics["top_devices"][0]["viewport"] == "393 x 873"

