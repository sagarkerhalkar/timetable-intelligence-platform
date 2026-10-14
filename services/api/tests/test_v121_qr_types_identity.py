from __future__ import annotations

import sqlite3
from pathlib import Path

from starlette.testclient import TestClient

from app.database import Database


def _create(client: TestClient, payload: dict[str, object]) -> dict[str, object]:
    response = client.post('/api/v1/qr-codes', json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['active'] is True
    return body


def test_all_seven_qr_types_create_and_are_active(client: TestClient) -> None:
    samples: dict[str, dict[str, object]] = {
        'url': {'qr_type': 'url', 'content': {'url': 'https://example.com/class'}},
        'calendar': {
            'qr_type': 'calendar',
            'content': {
                'title': 'Physics Test',
                'start': '2026-08-20T10:00:00+05:30',
                'end': '2026-08-20T11:00:00+05:30',
                'location': 'Bhopal',
            },
        },
        'contact': {
            'qr_type': 'contact',
            'content': {
                'full_name': 'Sagar Test',
                'phone': '+919876543210',
                'email': 'contact@example.com',
                'website': 'https://example.com',
            },
        },
        'email': {'qr_type': 'email', 'content': {'email': 'student@example.com', 'subject': 'Hello'}},
        'geo': {'qr_type': 'geo', 'content': {'latitude': 23.2599, 'longitude': 77.4126, 'label': 'Bhopal'}},
        'phone': {'qr_type': 'phone', 'content': {'phone': '+919876543210'}},
        'wifi': {
            'qr_type': 'wifi',
            'content': {'ssid': 'Classroom-WiFi', 'security': 'WPA', 'password': 'Secret1234'},
        },
    }
    created = [_create(client, payload) for payload in samples.values()]
    assert {item['qr_type'] for item in created} == set(samples)
    assert all(item['tracking_mode'] == 'tracked' for item in created)


def test_calendar_contact_and_native_actions(client: TestClient) -> None:
    calendar = _create(client, {
        'qr_type': 'calendar',
        'content': {'title': 'Parent Meeting', 'start': '2026-08-20T10:00:00+05:30'},
    })
    resolved = client.get(f"/api/v1/qr/resolve/{calendar['slug']}")
    assert resolved.status_code == 200
    assert resolved.json()['action_kind'] == 'download'
    action = client.get(f"/api/v1/qr/action/{calendar['slug']}")
    assert action.status_code == 200
    assert action.headers['content-type'].startswith('text/calendar')
    assert b'BEGIN:VCALENDAR' in action.content

    contact = _create(client, {'qr_type': 'contact', 'content': {'full_name': 'Teacher One'}})
    action = client.get(f"/api/v1/qr/action/{contact['slug']}")
    assert action.status_code == 200
    assert action.headers['content-type'].startswith('text/vcard')
    assert b'BEGIN:VCARD' in action.content

    email = _create(client, {'qr_type': 'email', 'content': {'email': 'teacher@example.com', 'subject': 'Test'}})
    resolved = client.get(f"/api/v1/qr/resolve/{email['slug']}").json()
    assert resolved['action_kind'] == 'redirect'
    assert resolved['action_url'].startswith('mailto:teacher@example.com')

    phone = _create(client, {'qr_type': 'phone', 'content': {'phone': '+919876543210'}})
    assert client.get(f"/api/v1/qr/resolve/{phone['slug']}").json()['action_url'].startswith('tel:')

    geo = _create(client, {'qr_type': 'geo', 'content': {'latitude': 23.2599, 'longitude': 77.4126, 'label': 'Bhopal'}})
    assert 'google.com/maps' in client.get(f"/api/v1/qr/resolve/{geo['slug']}").json()['action_url']


def test_wifi_supports_tracked_analytics_and_direct_join_qr(client: TestClient) -> None:
    tracked = _create(client, {
        'qr_type': 'wifi',
        'tracking_mode': 'tracked',
        'content': {'ssid': 'Students-WiFi', 'security': 'WPA', 'password': 'Classroom123'},
    })
    resolved = client.get(f"/api/v1/qr/resolve/{tracked['slug']}")
    assert resolved.status_code == 200
    body = resolved.json()
    assert body['action_kind'] == 'wifi'
    assert body['wifi']['ssid'] == 'Students-WiFi'

    wifi_image = client.get(f"/api/v1/qr/wifi/{tracked['slug']}/image")
    assert wifi_image.status_code == 200
    assert wifi_image.headers['content-type'] == 'image/png'
    assert wifi_image.content.startswith(b'\x89PNG\r\n\x1a\n')

    direct = _create(client, {
        'qr_type': 'wifi',
        'tracking_mode': 'direct',
        'content': {'ssid': 'Staff-WiFi', 'security': 'WPA', 'password': 'Private123'},
    })
    direct_image = client.get(f"/api/v1/qr-codes/{direct['id']}/image?format=png")
    assert direct_image.status_code == 200
    assert direct_image.content.startswith(b'\x89PNG\r\n\x1a\n')


def test_identify_with_email_is_explicit_and_repeat_device_is_deduped(client: TestClient) -> None:
    code = _create(client, {
        'qr_type': 'url',
        'tracking_mode': 'tracked',
        'identity_mode': 'email',
        'content': {'url': 'https://example.com/form'},
    })
    slug = code['slug']

    no_email = client.post(
        f'/api/v1/qr/confirm/{slug}',
        json={'visitor_id': 'browser-device-001', 'event_id': 'scan-event-001'},
    )
    assert no_email.status_code == 422

    common = {
        'visitor_id': 'browser-device-001',
        'scanner_email': 'student@example.com',
        'device_model': 'Pixel 8',
        'client_platform': 'Android 15',
        'timezone': 'Asia/Kolkata',
        'screen_width': 1080,
        'screen_height': 2400,
    }
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36',
        'cf-ipcountry': 'IN',
    }
    first = client.post(f'/api/v1/qr/confirm/{slug}', headers=headers, json={**common, 'event_id': 'scan-event-002'})
    second = client.post(f'/api/v1/qr/confirm/{slug}', headers=headers, json={**common, 'event_id': 'scan-event-003'})
    duplicate = client.post(f'/api/v1/qr/confirm/{slug}', headers=headers, json={**common, 'event_id': 'scan-event-003'})
    assert first.status_code == second.status_code == duplicate.status_code == 200
    assert first.json()['recorded'] is True
    assert second.json()['recorded'] is True
    assert duplicate.json()['recorded'] is False

    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics['total_scans'] == 2
    assert analytics['unique_visitors'] == 1
    assert analytics['unique_emails'] == 1
    assert analytics['identified_scans'] == 2
    assert analytics['anonymous_scans'] == 0
    assert analytics['device_models']['Pixel 8'] == 2
    assert len(analytics['top_devices']) == 1
    device = analytics['top_devices'][0]
    assert device['scans'] == 2
    assert device['scanner_email'] == 'student@example.com'
    assert device['device_model'] == 'Pixel 8'
    assert device['client_platform'] == 'Android 15'
    assert device['timezone'] == 'Asia/Kolkata'
    assert device['screen_resolution'] == '1080×2400'
    assert device['qr_codes'] == 1
    recent = analytics['recent_scans'][0]
    assert recent['client_platform'] == 'Android 15'
    assert recent['timezone'] == 'Asia/Kolkata'
    assert recent['screen_resolution'] == '1080×2400'


def test_email_identification_is_not_allowed_in_direct_mode(client: TestClient) -> None:
    response = client.post('/api/v1/qr-codes', json={
        'qr_type': 'url',
        'tracking_mode': 'direct',
        'identity_mode': 'email',
        'content': {'url': 'https://example.com'},
    })
    assert response.status_code == 422
    assert 'Tracked mode' in response.text


def test_v121_migrates_v120_saved_qr_database_before_new_indexes(tmp_path: Path) -> None:
    path = tmp_path / 'old-v120.db'
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE qr_codes (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
            target_url TEXT NOT NULL, public_base_url TEXT, short_url TEXT,
            design_json TEXT NOT NULL DEFAULT '{}', experience_json TEXT NOT NULL DEFAULT '{}',
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, qr_id TEXT NOT NULL, scanned_at TEXT NOT NULL,
            visitor_hash TEXT NOT NULL, event_hash TEXT, confirmed INTEGER NOT NULL DEFAULT 0,
            country TEXT NOT NULL DEFAULT 'Unknown', device_type TEXT NOT NULL DEFAULT 'Other',
            browser TEXT NOT NULL DEFAULT 'Other', operating_system TEXT NOT NULL DEFAULT 'Other',
            platform TEXT NOT NULL DEFAULT 'Direct / QR', source_confidence TEXT NOT NULL DEFAULT 'unknown',
            referrer_host TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '',
            screen_width INTEGER, screen_height INTEGER
        );
        """
    )
    connection.close()

    Database(path)
    connection = sqlite3.connect(path)
    code_columns = {row[1] for row in connection.execute('PRAGMA table_info(qr_codes)')}
    scan_columns = {row[1] for row in connection.execute('PRAGMA table_info(qr_scans)')}
    indexes = {row[1] for row in connection.execute("PRAGMA index_list('qr_scans')")}
    connection.close()

    assert {'qr_type', 'tracking_mode', 'identity_mode', 'payload_json'} <= code_columns
    assert {'timezone', 'scanner_email', 'device_model', 'client_platform', 'telemetry_json'} <= scan_columns
    assert {'idx_qr_scans_visitor', 'idx_qr_scans_email'} <= indexes


def test_anonymous_mode_collects_maximum_standard_device_telemetry(client: TestClient) -> None:
    code = _create(client, {
        'qr_type': 'url',
        'tracking_mode': 'tracked',
        'identity_mode': 'anonymous',
        'content': {'url': 'https://example.com/anonymous'},
    })
    response = client.post(
        f"/api/v1/qr/confirm/{code['slug']}",
        headers={
            'user-agent': 'Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/140.0.7339.80 Mobile Safari/537.36',
            'cf-ipcountry': 'IN',
        },
        json={
            'visitor_id': 'anonymous-device-telemetry-001',
            'event_id': 'anonymous-event-telemetry-001',
            'language': 'en-IN',
            'timezone': 'Asia/Kolkata',
            'screen_width': 1080,
            'screen_height': 2400,
            'device_model': 'Pixel 8',
            'client_platform': 'Android 15 · arm 64-bit',
            'telemetry': {
                'browser_version': 'Chrome 140.0.7339.80',
                'platform_version': '15',
                'architecture': 'arm',
                'bitness': '64',
                'form_factors': ['Mobile'],
                'device_memory_gb': 8,
                'hardware_concurrency': 8,
                'max_touch_points': 5,
                'pixel_ratio': 2.75,
                'color_depth': 24,
                'viewport_width': 393,
                'viewport_height': 873,
                'screen_orientation': 'portrait-primary',
                'connection_type': 'wifi',
                'effective_connection_type': '4g',
                'downlink_mbps': 10,
                'rtt_ms': 50,
                'save_data': False,
                'languages': ['en-IN', 'en'],
                'cookies_enabled': True,
                'browser_vendor': 'Google Inc.',
                'timezone_offset_minutes': -330,
                'standalone': False,
                'primary_pointer': 'coarse',
                'hover_capable': False,
                'color_gamut': 'p3',
            },
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()['recorded'] is True

    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics['total_scans'] == 1
    assert analytics['unique_visitors'] == 1
    assert analytics['anonymous_scans'] == 1
    assert analytics['memory_classes']['8 GB'] == 1
    assert analytics['cpu_cores']['8 cores'] == 1
    assert analytics['connection_types']['4g'] == 1

    device = analytics['top_devices'][0]
    assert device['browser_version'] == 'Chrome 140.0.7339.80'
    assert device['platform_version'] == '15'
    assert device['architecture'] == 'arm'
    assert device['bitness'] == '64'
    assert device['device_memory_gb'] == 8
    assert device['hardware_concurrency'] == 8
    assert device['max_touch_points'] == 5
    assert device['pixel_ratio'] == 2.75
    assert device['viewport_width'] == 393
    assert device['viewport_height'] == 873
    assert device['viewport'] == '393 x 873'
    assert device['color_depth'] == 24
    assert device['connection'] == 'wifi · 4g effective'
    assert '10 Mbps' in device['network_quality']
    assert device['form_factors'] == 'Mobile'
    assert device['screen_orientation'] == 'portrait-primary'
    assert device['browser_vendor'] == 'Google Inc.'
    assert device['cookies_enabled'] is True
    assert device['standalone'] is False
    assert 'coarse pointer' in device['input_capability']
    assert '5 touch' in device['input_capability']
    assert device['color_gamut'] == 'p3'
    assert device['languages'] == 'en-IN, en'
    assert device['timezone_offset_minutes'] == -330

    recent = analytics['recent_scans'][0]
    assert recent['browser_version'] == 'Chrome 140.0.7339.80'
    assert recent['device_memory_gb'] == 8
    assert recent['hardware_concurrency'] == 8
    assert recent['connection'] == 'wifi · 4g effective'

    exported = client.get(f"/api/v1/qr-scans/export.csv?qr_id={code['id']}")
    assert exported.status_code == 200
    assert 'Approx RAM GB' in exported.text
    assert 'Chrome 140.0.7339.80' in exported.text
    assert 'Google Inc.' in exported.text


def test_first_party_cookie_preserves_anonymous_device_when_payload_id_changes(client: TestClient) -> None:
    code = _create(client, {
        'qr_type': 'url',
        'tracking_mode': 'tracked',
        'identity_mode': 'anonymous',
        'content': {'url': 'https://example.com/device-continuity'},
    })
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36',
        'cf-ipcountry': 'IN',
    }
    first = client.post(
        f"/api/v1/qr/confirm/{code['slug']}",
        headers=headers,
        json={'visitor_id': 'local-storage-id-first', 'event_id': 'cookie-device-event-001'},
    )
    assert first.status_code == 200, first.text
    assert first.json()['recorded'] is True
    assert client.cookies.get('tti_qr_visitor') == 'local-storage-id-first'

    # Simulate localStorage being regenerated while the first-party cookie remains.
    second = client.post(
        f"/api/v1/qr/confirm/{code['slug']}",
        headers=headers,
        json={'visitor_id': 'local-storage-id-changed', 'event_id': 'cookie-device-event-002'},
    )
    assert second.status_code == 200, second.text
    assert second.json()['recorded'] is True

    analytics = client.get(f"/api/v1/qr-analytics?qr_id={code['id']}").json()
    assert analytics['total_scans'] == 2
    assert analytics['unique_visitors'] == 1
    assert analytics['top_devices'][0]['scans'] == 2
