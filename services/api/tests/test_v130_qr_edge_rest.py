"""QR edge sync through the Cloudflare REST API (no wrangler, no npx).

A fake Cloudflare answers here; nothing touches the real account, and the
runtime cache/log files go to a temporary folder, never the live data folder.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

from app.services import qr_edge_runtime as edge

ACCOUNT = edge.ACCOUNT_ID
NS_LIVE = "0a1c82f1062b403cab2a74e828d7e344"
NS_STALE = "5936d23cdbf24c0890effd4c41e10c19"
VERSION = "1b2c3d4e-0000-4000-8000-000000000001"


class FakeCloudflare:
    def __init__(self, token: str = "good-token") -> None:
        self.token = token
        self.kv: dict[tuple[str, str], bytes] = {}
        self.calls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(f"{request.method} {request.url.path}")
        if request.headers.get("authorization") != f"Bearer {self.token}":
            return httpx.Response(401, json={"success": False, "errors": [{"code": 9109, "message": "Invalid access token"}]})
        path = request.url.path.replace("/client/v4", "")
        base = f"/accounts/{ACCOUNT}/workers/scripts/q"
        if path == base + "/deployments":
            return httpx.Response(200, json={"success": True, "result": {"deployments": [
                {"id": "d2", "versions": [{"version_id": VERSION, "percentage": 100}]},
                {"id": "d1", "versions": [{"version_id": "old-version", "percentage": 100}]},
            ]}})
        if path == f"{base}/versions/{VERSION}":
            return httpx.Response(200, json={"success": True, "result": {"id": VERSION, "resources": {"bindings": [
                {"name": "QR_EDGE", "type": "kv_namespace", "namespace_id": NS_LIVE},
                {"name": "QR_EDGE", "type": "kv_namespace", "namespace_id": NS_STALE},
            ]}}})
        if path == f"/accounts/{ACCOUNT}/storage/kv/namespaces":
            return httpx.Response(200, json={"success": True, "result": [{"id": NS_LIVE, "title": "nexttoppers_qr_edge"}],
                                             "result_info": {"page": 1, "total_pages": 1}})
        prefix = f"/accounts/{ACCOUNT}/storage/kv/namespaces/"
        if path.startswith(prefix) and "/values/" in path:
            ns, key = path[len(prefix):].split("/values/", 1)
            key = unquote(key)
            if request.method == "PUT":
                self.kv[(ns, key)] = request.content
                return httpx.Response(200, json={"success": True, "result": None})
            if (ns, key) in self.kv:
                return httpx.Response(200, content=self.kv[(ns, key)])
            return httpx.Response(404, json={"success": False, "errors": [{"code": 10009, "message": "key not found"}]})
        return httpx.Response(404, json={"success": False, "errors": [{"code": 7003, "message": "no route"}]})


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeCloudflare:
    cf = FakeCloudflare()
    monkeypatch.setattr(edge, "_TRANSPORT", httpx.MockTransport(cf))
    monkeypatch.setattr(edge, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(edge, "_CACHE_FILE", tmp_path / "qr_edge_runtime.json")
    monkeypatch.setattr(edge, "_LOG_FILE", tmp_path / "qr_edge_sync.log")
    monkeypatch.setenv("NEXTTOPPERS_QR_EDGE_SYNC", "on")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "good-token")
    monkeypatch.setattr(edge.time, "sleep", lambda _s: None)
    return cf


def _record(**over: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": "abc", "slug": "5wqrrpw", "name": "Brochure", "qr_type": "url", "tracking_mode": "tracked",
        "identity_mode": "anonymous", "target_url": "https://example.com/?a=1&utm_medium=qr", "active": True,
        "experience": {}, "updated_at": "2026-10-14T00:00:00Z",
    }
    record.update(over)
    return record


def test_sync_writes_route_to_the_live_namespace_only(fake: FakeCloudflare) -> None:
    edge.sync_qr_record(_record())
    assert set(fake.kv) == {(NS_LIVE, "qr:5wqrrpw")}
    stored = json.loads(fake.kv[(NS_LIVE, "qr:5wqrrpw")])
    assert stored["target_url"] == "https://example.com/?a=1&utm_medium=qr"
    assert stored["slug"] == "5wqrrpw" and stored["active"] is True
    assert not any("old-version" in call for call in fake.calls)


def test_edit_keeps_slug_and_namespace_lookup_is_cached(fake: FakeCloudflare) -> None:
    edge.sync_qr_record(_record())
    discovery_calls = sum("deployments" in c for c in fake.calls)
    edge.sync_qr_record(_record(target_url="https://example.com/new"))
    assert sum("deployments" in c for c in fake.calls) == discovery_calls
    assert json.loads(fake.kv[(NS_LIVE, "qr:5wqrrpw")])["target_url"] == "https://example.com/new"


def test_deactivate_marks_route_inactive(fake: FakeCloudflare) -> None:
    edge.deactivate_qr_record(_record())
    assert json.loads(fake.kv[(NS_LIVE, "qr:5wqrrpw")])["active"] is False


def test_direct_qr_is_never_synced(fake: FakeCloudflare) -> None:
    edge.sync_qr_record(_record(tracking_mode="direct"))
    assert fake.calls == []


def test_wrong_token_gives_a_clear_fix_message(fake: FakeCloudflare, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "wrong")
    with pytest.raises(edge.QrEdgeSyncError) as info:
        edge.sync_qr_record(_record())
    message = str(info.value)
    assert "Invalid access token" in message and "FIX_QR_CLOUDFLARE_TOKEN.ps1" in message
    assert "\x1b" not in message
    assert fake.kv == {}


def test_bearer_prefix_and_quotes_in_token_are_tolerated(fake: FakeCloudflare, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", '"Bearer good-token"')
    edge.sync_qr_record(_record())
    assert (NS_LIVE, "qr:5wqrrpw") in fake.kv


def test_switch_off_skips_cloudflare(fake: FakeCloudflare, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTTOPPERS_QR_EDGE_SYNC", "off")
    edge.sync_qr_record(_record())
    edge.deactivate_qr_record(_record())
    assert fake.calls == []


def test_wrangler_output_is_cleaned_and_explains_the_token() -> None:
    raw = (
        "\x1b[31mX \x1b[41;31m[\x1b[41;97mERROR\x1b[41;31m]\x1b[0m \x1b[1mIn a non-interactive environment, "
        "it's necessary to set a CLOUDFLARE_API_TOKEN environment variable for wrangler to work.\x1b[0m\n"
        'Logs were written to "C:\\\\WINDOWS\\\\system32\\\\x.log"\n'
    )
    import subprocess

    text = edge._combined(subprocess.CompletedProcess(["wrangler"], 1, "", raw))
    assert "\x1b" not in text and "Logs were written" not in text
    assert text.startswith(edge.TOKEN_HELP)
