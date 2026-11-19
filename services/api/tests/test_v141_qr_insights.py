"""QR Insights (Nov 2026): read-only analytics with honest source and location labels."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.api import qr_insights, qr_scale
from app.api.qr_insights import classify_source, network_name
from app.database import Database


@pytest.mark.parametrize(
    ("platform", "confidence", "host", "label", "how"),
    [
        ("Direct / QR", "unknown", "", "Camera scan or app link (not reported)", "not_reported"),
        ("Google", "detected", "com.google.android.googlequicksearchbox", "Google Lens / Google app", "detected"),
        ("Google", "detected", "www.google.com", "Google Search", "detected"),
        ("Google", "detected", "google.co.in", "Google Search", "detected"),
        ("Google", "detected", "com.google.android.youtube", "YouTube", "detected"),
        ("Google", "detected", "com.google.android.gm", "Gmail", "detected"),
        ("Web / Website", "detected", "webqr.com", "Online QR scanner website", "detected"),
        ("WhatsApp", "exact", "", "WhatsApp", "tagged"),
        ("youtube", "exact", "", "YouTube", "tagged"),
        ("chatgpt.com", "exact", "", "ChatGPT", "tagged"),
        ("sms", "exact", "", "SMS", "tagged"),
        ("Web / Website", "detected", "example.org", "example.org", "detected"),
        ("Google", "detected", "", "Google (app or search)", "detected"),
    ],
)
def test_source_labels(platform: str, confidence: str, host: str, label: str, how: str) -> None:
    result = classify_source(platform, confidence, host)
    assert result["label"] == label and result["how"] == how


def test_network_names() -> None:
    assert network_name("Reliance Jio Infocomm Limited") == "Jio"
    assert network_name("Bharti Airtel Ltd.") == "Airtel"
    assert network_name("Vodafone Idea Ltd") == "Vi (Vodafone Idea)"
    assert network_name("") == "Not reported"


def test_overview_counts_only_verified_human_scans_and_changes_nothing(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    for module in (qr_insights, qr_scale):
        monkeypatch.setattr(module, "get_database", lambda: database)
    qr_insights._CACHE.clear()
    now = datetime.now(UTC).isoformat()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO qr_codes(id,name,slug,target_url,created_at,updated_at) VALUES('q1','Physics','phy01','https://example.com',?,?)",
            (now, now),
        )
    edge = json.dumps({"edge": {"region": "Bihar", "city": "Patna", "asOrganization": "Reliance Jio Infocomm Limited"}})
    rows = [
        ("v1", 1, "Mobile", "Direct / QR", "unknown", ""),
        ("v1", 1, "Mobile", "Google", "detected", "com.google.android.googlequicksearchbox"),
        ("v2", 1, "Mobile", "WhatsApp", "exact", ""),
        ("v3", 1, "bot", "Direct / QR", "unknown", ""),
        ("v4", 0, "Mobile", "Direct / QR", "legacy", ""),
    ]
    for n, (visitor, confirmed, device, platform, confidence, host) in enumerate(rows):
        database.record_qr_scan(
            qr_id="q1", scanned_at=datetime.now(UTC) - timedelta(minutes=n), visitor_hash=visitor, event_hash=f"e{n}",
            confirmed=bool(confirmed), country="IN", device_type=device, browser="Chrome", platform=platform,
            source_confidence=confidence, referrer_host=host, telemetry_json=edge,
        )
    with database.connect() as connection:
        before = connection.execute("SELECT COUNT(*), total_changes() FROM qr_scans").fetchone()[0]

    data = qr_insights.overview(period="30d", qr_id="")
    assert data["totals"]["scans"] == 3
    assert data["totals"]["unique_devices"] == 2
    assert data["totals"]["returning_devices"] == 1
    labels = {s["label"]: s["scans"] for s in data["sources"]}
    assert labels == {"Camera scan or app link (not reported)": 1, "Google Lens / Google app": 1, "WhatsApp": 1}
    assert data["states"][0]["state"] == "Bihar" and data["cities"][0]["city"] == "Patna"
    assert data["networks"][0]["label"] == "Jio"
    assert sum(data["hours"]) == 3 and sum(data["weekdays"]) == 3
    assert data["trend"][-1]["scans"] >= 1

    one = qr_insights.overview(period="7d", qr_id="q1")
    assert one["qr_name"] == "Physics" and one["totals"]["scans"] == 3
    with pytest.raises(Exception):
        qr_insights.overview(period="7d", qr_id="missing")
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM qr_scans").fetchone()[0] == before


def test_recent_scans_include_readable_source(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    monkeypatch.setattr(qr_scale, "get_database", lambda: database)
    qr_scale.ensure_qr_scale_schema()
    now = datetime.now(UTC).isoformat()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO qr_codes(id,name,slug,target_url,created_at,updated_at) VALUES('q2','Maths','mat01','https://example.com',?,?)",
            (now, now),
        )
    database.record_qr_scan(
        qr_id="q2", scanned_at=datetime.now(UTC), visitor_hash="v", event_hash="r1", confirmed=True, country="IN",
        device_type="Mobile", browser="Chrome", platform="Google", source_confidence="detected",
        referrer_host="com.google.android.googlequicksearchbox",
        telemetry_json=json.dumps({"edge": {"region": "Delhi", "city": "Delhi", "asOrganization": "Bharti Airtel"}}),
    )
    item = qr_scale.qr_scale_recent_scans(limit=25, cursor=None, qr_id="")["items"][0]
    assert item["source"]["label"] == "Google Lens / Google app"
    assert item["region"] == "Delhi" and item["network"] == "Airtel"


@pytest.mark.parametrize(
    ("ua", "expected"),
    [
        ("Mozilla/5.0 (Linux; Android 14; SM-A146B Build/UP1A; wv) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36 Instagram 358.0.0.0.62 Android", "Instagram"),
        ("Mozilla/5.0 (Linux; Android 13; wv) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/489.0.0.0;]", "Facebook"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 [FBAN/FBIOS;FBAV/470.0]", "Facebook"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Snapchat/13.20.0.43", "Snapchat"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 LinkedInApp", "LinkedIn"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/330.0.661532000 Mobile/15E148 Safari/604.1", "Google app"),
    ],
)
def test_in_app_browsers_are_detected_from_one_normal_link(ua: str, expected: str) -> None:
    from app.api.qr_fast import _platform

    platform, confidence = _platform("", "", ua)
    assert (platform, confidence) == (expected, "detected")
    assert classify_source(platform, confidence, "")["how"] == "detected"


def test_plain_chrome_and_tags_unchanged() -> None:
    from app.api.qr_fast import _platform

    chrome = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36"
    assert _platform("", "", chrome) == ("Direct / QR", "unknown")
    assert _platform("?src=whatsapp", "", chrome) == ("WhatsApp", "exact")
    assert _platform("", "android-app://com.whatsapp/", chrome) == ("WhatsApp", "detected")


def _seed(database: Database, n: int = 3) -> None:
    now = datetime.now(UTC).isoformat()
    with database.connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO qr_codes(id,name,slug,target_url,created_at,updated_at) VALUES('g1','Geo QR','geo01','https://example.com',?,?)",
            (now, now),
        )
    places = [("Bihar", "Patna", "Reliance Jio Infocomm Limited"), ("Bihar", "Gaya", "Bharti Airtel"), ("Delhi", "Delhi", "Bharti Airtel")]
    for i in range(n):
        region, city, org = places[i % len(places)]
        database.record_qr_scan(
            qr_id="g1", scanned_at=datetime.now(UTC) - timedelta(minutes=i), visitor_hash=f"d{i % 2}", event_hash=f"geo-{i}-{n}",
            confirmed=True, country="IN", device_type="Mobile", browser="Chrome", platform="Direct / QR",
            source_confidence="unknown", referrer_host="",
            telemetry_json=json.dumps({"edge": {"region": region, "city": city, "asOrganization": org}}),
        )


def _point(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    monkeypatch.setattr(qr_insights, "get_database", lambda: database)
    qr_insights._CACHE.clear()


def test_location_details_and_csv_downloads(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point(monkeypatch, database)
    _seed(database, 3)
    data = qr_insights.locations(period="30d", qr_id="")
    places = {(i["state"], i["city"]): i for i in data["items"]}
    assert data["total_scans"] == 3
    assert places[("Bihar", "Patna")]["network"] == "Jio"
    assert places[("Delhi", "Delhi")]["network"] == "Airtel"
    assert all(i["devices"] >= 1 and i["last_scan"] for i in data["items"])

    loc = qr_insights.locations_csv(period="30d", qr_id="")
    text = loc.body.decode("utf-8-sig")
    assert text.splitlines()[0].startswith('Country,State / Region,"City (approx.')
    assert "Patna" in text and 'attachment; filename="nexttoppers-qr-locations-30d' in loc.headers["content-disposition"]

    scans = qr_insights.scans_csv(period="30d", qr_id="g1")
    lines = scans.body.decode("utf-8-sig").splitlines()
    assert len(lines) == 4 and "Camera scan or app link (not reported)" in lines[1]
    assert any("Patna" in line and "Jio" in line for line in lines[1:])


def test_location_memo_reads_new_scans_only_once(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point(monkeypatch, database)
    _seed(database, 2)
    memo = qr_insights._geo(database)
    first_max = memo.max_id
    _seed(database, 3)  # adds three more scans
    memo = qr_insights._geo(database)
    assert memo.max_id > first_max
    assert {memo.get(i)[1] for i in range(1, memo.max_id + 1)} >= {"Patna", "Gaya", "Delhi"}


def test_cached_answer_is_served_instantly_while_refreshing(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
    _point(monkeypatch, database)
    _seed(database, 3)
    first = qr_insights.overview(period="30d", qr_id="")
    key = (str(database.path), "30d", "")
    stamp, value = qr_insights._CACHE[key]
    qr_insights._CACHE[key] = (stamp - 3600, value)  # pretend it is an hour old
    calls: list[int] = []
    monkeypatch.setattr(qr_insights, "_refresh_in_background", lambda k: calls.append(1))
    again = qr_insights.overview(period="30d", qr_id="")
    assert again["totals"]["scans"] == first["totals"]["scans"] and calls == [1]
