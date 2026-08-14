from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..dependencies import get_database

router = APIRouter(prefix="/api/v1/qr-fast", tags=["qr-fast"])

_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{2,80}$")
_BOT_RE = re.compile(r"bot|crawl|spider|slurp|headless|preview|facebookexternalhit|whatsapp", re.I)
_API_DIR = Path(__file__).resolve().parents[2]
_EDGE_SECRET_PATH = _API_DIR / "data" / "qr_edge_sync_secret.txt"
_EDGE_SYNC_URL = os.environ.get(
    "NEXTTOPPERS_QR_EDGE_SYNC_URL",
    "https://q.nexttoppers.workers.dev/__ntqr_admin/sync",
).strip()
_EDGE_SYNC_DISABLED = os.environ.get("NEXTTOPPERS_QR_EDGE_SYNC_DISABLED", "").strip() == "1"

_edge_lock = threading.Lock()
_edge_thread: threading.Thread | None = None
_edge_stop = threading.Event()
_edge_last_snapshot: dict[str, str] = {}
_edge_status: dict[str, object] = {
    "enabled": False,
    "running": False,
    "last_ok": False,
    "last_sync_at": "",
    "last_error": "",
    "route_count": 0,
    "changed": 0,
    "deleted": 0,
}


class FastScanEvent(BaseModel):
    event_id: str = ""
    visitor_id: str = ""
    user_agent: str = ""
    language: str = ""
    timezone: str = ""
    referrer: str = ""
    query: str = ""
    scanner_email: str = ""
    client_platform: str = ""
    device_model: str = ""
    screen_width: int | None = None
    screen_height: int | None = None
    edge: dict[str, object] = {}
    telemetry: dict[str, object] = {}


def _clip(value: object, limit: int) -> str:
    return str(value or "")[:limit]


def _browser(ua: str) -> str:
    tests = (
        ("Edge", r"Edg/"), ("Opera", r"OPR/|Opera"), ("Samsung Internet", r"SamsungBrowser/"),
        ("Chrome", r"Chrome/|CriOS/"), ("Firefox", r"Firefox/|FxiOS/"), ("Safari", r"Safari/"),
    )
    for name, pattern in tests:
        if re.search(pattern, ua, re.I):
            return name
    return "Other"


def _os(ua: str) -> str:
    tests = (
        ("Android", r"Android"), ("iOS", r"iPhone|iPad|iPod"), ("Windows", r"Windows NT"),
        ("macOS", r"Macintosh|Mac OS X"), ("ChromeOS", r"CrOS"), ("Linux", r"Linux"),
    )
    for name, pattern in tests:
        if re.search(pattern, ua, re.I):
            return name
    return "Other"


def _device(ua: str) -> str:
    if _BOT_RE.search(ua):
        return "bot"
    if re.search(r"iPad|Tablet|Android(?!.*Mobile)", ua, re.I):
        return "Tablet"
    if re.search(r"Mobile|iPhone|iPod|Android", ua, re.I):
        return "Mobile"
    if ua:
        return "Desktop"
    return "Other"


def _platform(query: str, referrer: str) -> tuple[str, str]:
    parsed = parse_qs(query.lstrip("?"), keep_blank_values=False)
    for key in ("nt_source", "source", "channel", "utm_source", "src"):
        values = parsed.get(key)
        if values and values[0]:
            raw = _clip(values[0], 80)
            named = {
                "whatsapp": "WhatsApp", "telegram": "Telegram", "instagram": "Instagram",
                "facebook": "Facebook", "googlechat": "Google Chat", "google_chat": "Google Chat",
                "web": "Web", "email": "Email",
            }.get(raw.lower(), raw)
            return named, "exact"
    host = ""
    try:
        host = (urlparse(referrer).hostname or "").lower()
    except ValueError:
        host = ""
    detected = (
        ("whatsapp", "WhatsApp"), ("t.me", "Telegram"), ("telegram", "Telegram"),
        ("instagram", "Instagram"), ("facebook", "Facebook"), ("google", "Google"),
    )
    for token, label in detected:
        if token in host:
            return label, "detected"
    return "Direct / QR", "unknown"


def _safe_experience(raw: object) -> dict[str, object]:
    if isinstance(raw, str):
        try:
            value = json.loads(raw or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            value = {}
    elif isinstance(raw, dict):
        value = raw
    else:
        value = {}
    if not isinstance(value, dict):
        value = {}
    return {
        "mode": str(value.get("mode") or "brand")[:12],
        "asset_id": _clip(value.get("asset_id"), 80) or None,
        "title": _clip(value.get("title") or "NextToppers", 80),
        "message": _clip(value.get("message") or "Opening your content…", 160),
        "accent_color": _clip(value.get("accent_color") or "#2455FF", 24),
        "background_color": _clip(value.get("background_color") or "#F8FAFC", 24),
        "redirect_delay_ms": max(0, min(120, int(value.get("redirect_delay_ms") or 0))),
        "logo_scale_percent": max(15, min(65, int(value.get("logo_scale_percent") or 28))),
        "image_fit": "contain" if value.get("image_fit") == "contain" else "cover",
        "image_scale_percent": max(35, min(100, int(value.get("image_scale_percent") or 100))),
    }


def _route_from_row(row) -> dict[str, object]:
    return {
        "ok": True,
        "id": str(row["id"]),
        "slug": str(row["slug"]),
        "name": str(row["name"] or "NextToppers QR"),
        "qr_type": str(row["qr_type"] or "url"),
        "tracking_mode": str(row["tracking_mode"] or "tracked"),
        "identity_mode": str(row["identity_mode"] or "anonymous"),
        "target_url": str(row["target_url"] or "").strip(),
        "active": bool(row["active"]),
        "experience": _safe_experience(row["experience_json"]),
        "updated_at": str(row["updated_at"] or ""),
    }


def _lightweight_qr_row(slug: str):
    if not _SLUG_RE.fullmatch(slug):
        return None
    database = get_database()
    with database.connect() as connection:
        return connection.execute(
            """
            SELECT id,name,slug,qr_type,tracking_mode,identity_mode,target_url,
                   experience_json,active,updated_at
            FROM qr_codes
            WHERE slug=?
            LIMIT 1
            """,
            (slug,),
        ).fetchone()


def _edge_snapshot() -> dict[str, dict[str, object]]:
    database = get_database()
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT id,name,slug,qr_type,tracking_mode,identity_mode,target_url,
                   experience_json,active,updated_at
            FROM qr_codes
            WHERE slug IS NOT NULL AND TRIM(slug) <> ''
            ORDER BY slug
            """
        ).fetchall()
    out: dict[str, dict[str, object]] = {}
    for row in rows:
        slug = str(row["slug"] or "").strip()
        if _SLUG_RE.fullmatch(slug):
            out[slug] = _route_from_row(row)
    return out


def _edge_secret() -> str:
    try:
        value = _EDGE_SECRET_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if len(value) < 32:
        return ""
    return value


def _edge_post(payload: dict[str, object], secret: str) -> dict[str, object]:
    body = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        _EDGE_SYNC_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "x-ntqr-sync-secret": secret,
            "user-agent": "NextToppers-QR-Edge-Sync/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        raw = response.read(131072)
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"edge sync HTTP {response.status}")
    try:
        result = json.loads(raw.decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("edge sync returned invalid JSON") from exc
    if not isinstance(result, dict) or not bool(result.get("ok")):
        raise RuntimeError(f"edge sync rejected: {result}")
    return result


def _fingerprint(route: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(route, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _set_edge_status(**updates: object) -> None:
    with _edge_lock:
        _edge_status.update(updates)


def _edge_sync_once(force_replace: bool = False) -> None:
    global _edge_last_snapshot

    secret = _edge_secret()
    if not secret or _EDGE_SYNC_DISABLED:
        _set_edge_status(enabled=False, running=False)
        return

    routes = _edge_snapshot()
    current = {slug: _fingerprint(route) for slug, route in routes.items()}
    previous = dict(_edge_last_snapshot)

    if force_replace or not previous:
        payload = {"mode": "replace", "routes": list(routes.values())}
        changed = len(routes)
        deleted = 0
    else:
        changed_slugs = [slug for slug, fp in current.items() if previous.get(slug) != fp]
        deleted_slugs = [slug for slug in previous if slug not in current]
        if not changed_slugs and not deleted_slugs:
            _set_edge_status(
                enabled=True,
                running=True,
                last_ok=True,
                last_sync_at=datetime.now(UTC).isoformat(),
                last_error="",
                route_count=len(routes),
                changed=0,
                deleted=0,
            )
            return
        payload = {
            "mode": "delta",
            "routes": [routes[slug] for slug in changed_slugs],
            "deletes": deleted_slugs,
        }
        changed = len(changed_slugs)
        deleted = len(deleted_slugs)

    result = _edge_post(payload, secret)
    _edge_last_snapshot = current
    _set_edge_status(
        enabled=True,
        running=True,
        last_ok=True,
        last_sync_at=datetime.now(UTC).isoformat(),
        last_error="",
        route_count=len(routes),
        changed=int(result.get("upserts") or changed),
        deleted=int(result.get("deletes") or deleted),
    )


def _edge_sync_loop() -> None:
    _set_edge_status(enabled=True, running=True)
    first = True
    while not _edge_stop.is_set():
        try:
            _edge_sync_once(force_replace=first)
            first = False
        except Exception as exc:
            _set_edge_status(
                enabled=True,
                running=True,
                last_ok=False,
                last_error=_clip(exc, 500),
            )
        _edge_stop.wait(1.0)


@router.on_event("startup")
def start_edge_sync() -> None:
    global _edge_thread
    if _EDGE_SYNC_DISABLED or not _edge_secret():
        _set_edge_status(enabled=False, running=False)
        return
    with _edge_lock:
        if _edge_thread is not None and _edge_thread.is_alive():
            return
        _edge_stop.clear()
        _edge_thread = threading.Thread(
            target=_edge_sync_loop,
            name="nexttoppers-qr-edge-sync",
            daemon=True,
        )
        _edge_thread.start()


@router.on_event("shutdown")
def stop_edge_sync() -> None:
    _edge_stop.set()


@router.get("/health")
def qr_fast_health() -> dict[str, object]:
    with _edge_lock:
        status = dict(_edge_status)
    return {"ok": True, "service": "qr-fast", "mode": "edge-kv-route", "edge_sync": status}


@router.get("/edge-sync-status")
def qr_fast_edge_sync_status() -> dict[str, object]:
    with _edge_lock:
        return {"ok": True, **dict(_edge_status)}


@router.get("/{slug}/resolve")
def qr_fast_resolve(slug: str) -> dict[str, object]:
    row = _lightweight_qr_row(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    route = _route_from_row(row)
    if not bool(route["active"]):
        raise HTTPException(status_code=410, detail="QR code is inactive")
    if not str(route["target_url"] or "").strip():
        raise HTTPException(status_code=422, detail="QR destination is empty")
    return route


@router.post("/{slug}/confirm")
def qr_fast_confirm(slug: str, event: FastScanEvent) -> dict[str, object]:
    row = _lightweight_qr_row(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not bool(row["active"]):
        raise HTTPException(status_code=410, detail="QR code is inactive")

    ua = _clip(event.user_agent, 700)
    visitor_seed = _clip(event.visitor_id, 160) or "|".join(
        (ua, _clip(event.language, 80), _clip(event.timezone, 80), str(event.screen_width or 0), str(event.screen_height or 0))
    )
    event_seed = _clip(event.event_id, 160) or f"{slug}|{visitor_seed}|{datetime.now(UTC).isoformat()}"
    visitor_hash = hashlib.sha256(visitor_seed.encode("utf-8", "ignore")).hexdigest()
    event_hash = hashlib.sha256(event_seed.encode("utf-8", "ignore")).hexdigest()

    referrer = _clip(event.referrer, 1000)
    try:
        referrer_host = _clip(urlparse(referrer).hostname or "", 255)
    except ValueError:
        referrer_host = ""
    platform, confidence = _platform(_clip(event.query, 1000), referrer)
    edge = event.edge if isinstance(event.edge, dict) else {}
    country = _clip(edge.get("country") or "Unknown", 80)
    email = _clip(event.scanner_email, 254).strip().lower()

    telemetry = {
        "fast_path": True,
        "edge_kv_route": True,
        "edge": {k: edge.get(k) for k in ("colo", "city", "region", "regionCode", "continent", "timezone", "asn", "asOrganization", "httpProtocol", "tlsVersion", "clientTcpRtt", "clientQuicRtt") if edge.get(k) is not None},
        "browser": event.telemetry if isinstance(event.telemetry, dict) else {},
    }
    telemetry_json = json.dumps(telemetry, ensure_ascii=True, separators=(",", ":"))[:12000]

    database = get_database()
    inserted = database.record_qr_scan(
        qr_id=str(row["id"]),
        scanned_at=datetime.now(UTC),
        visitor_hash=visitor_hash,
        event_hash=event_hash,
        confirmed=True,
        country=country or "Unknown",
        device_type=_device(ua),
        browser=_browser(ua),
        operating_system=_os(ua),
        platform=_clip(platform, 80) or "Direct / QR",
        source_confidence=confidence,
        referrer_host=referrer_host,
        language=_clip(event.language, 80),
        timezone=_clip(event.timezone, 80),
        scanner_email=email,
        device_model=_clip(event.device_model, 160),
        client_platform=_clip(event.client_platform, 160),
        telemetry_json=telemetry_json,
        screen_width=max(0, min(20000, int(event.screen_width))) if event.screen_width is not None else None,
        screen_height=max(0, min(20000, int(event.screen_height))) if event.screen_height is not None else None,
    )
    return {"ok": True, "recorded": inserted is not None}
