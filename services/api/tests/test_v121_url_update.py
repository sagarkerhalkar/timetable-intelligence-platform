from fastapi.testclient import TestClient


def test_url_qr_target_edit_updates_canonical_content_and_preserves_slug(client: TestClient) -> None:
    created = client.post(
        "/api/v1/qr-codes",
        json={"qr_type": "url", "target_url": "https://example.com/first", "name": "Editable URL"},
    )
    assert created.status_code == 201, created.text
    original = created.json()

    changed = client.patch(
        f"/api/v1/qr-codes/{original['id']}",
        json={"target_url": "https://example.com/updated"},
    )
    assert changed.status_code == 200, changed.text
    updated = changed.json()
    assert updated["slug"] == original["slug"]
    assert updated["target_url"] == "https://example.com/updated"
    assert updated["content"]["url"] == "https://example.com/updated"

    fetched = client.get(f"/api/v1/qr-codes/{original['id']}")
    assert fetched.status_code == 200, fetched.text
    persisted = fetched.json()
    assert persisted["target_url"] == "https://example.com/updated"
    assert persisted["content"]["url"] == "https://example.com/updated"
