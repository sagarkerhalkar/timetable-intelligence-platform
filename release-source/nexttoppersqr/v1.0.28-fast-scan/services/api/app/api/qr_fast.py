from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..dependencies import get_database

router = APIRouter(prefix="/api/v1/qr-fast", tags=["qr-fast"])

_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{2,80}$")
_BOT_RE = re.compile(r"bot|crawl|spider|slurp|headless|preview|facebookexternalhit|whatsapp", re.I)


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
        ("macOS", r"Macintosh|Mac OS X"), ("Linux", r"Linux"), ("ChromeOS", r"CrOS"),
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


def _lightweight_qr_row(slug: str):
    if not _SLUG_RE.fullmatch(slug):
        return None
    database = get_database()
    with database.connect() as connection:
        return connection.execute(
            """
            SELECT id,name,slug,qr_type,tracking_mode,identity_mode,target_url,payload_json,
                   experience_json,active,updated_at
            FROM qr_codes
            WHERE slug=?
            LIMIT 1
            """,
            (slug,),
        ).fetchone()


@router.get("/health")
def qr_fast_health() -> dict[str, object]:
    return {"ok": True, "service": "qr-fast", "mode": "edge-resolve"}


@router.get("/{slug}/resolve")
def qr_fast_resolve(slug: str) -> dict[str, object]:
    row = _lightweight_qr_row(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not bool(row["active"]):
        raise HTTPException(status_code=410, detail="QR code is inactive")
    target = str(row["target_url"] or "").strip()
    if not target:
        raise HTTPException(status_code=422, detail="QR destination is empty")
    try:
        experience = json.loads(str(row["experience_json"] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        experience = {}
    if not isinstance(experience, dict):
        experience = {}
    safe_experience = {
        "mode": str(experience.get("mode") or "brand")[:12],
        "asset_id": _clip(experience.get("asset_id"), 80) or None,
        "title": _clip(experience.get("title") or "NextToppers", 80),
        "message": _clip(experience.get("message") or "Opening your content…", 160),
        "accent_color": _clip(experience.get("accent_color") or "#2455FF", 24),
        "background_color": _clip(experience.get("background_color") or "#F8FAFC", 24),
        "redirect_delay_ms": max(120, min(5000, int(experience.get("redirect_delay_ms") or 650))),
        "logo_scale_percent": max(15, min(65, int(experience.get("logo_scale_percent") or 28))),
        "image_fit": "contain" if experience.get("image_fit") == "contain" else "cover",
        "image_scale_percent": max(35, min(100, int(experience.get("image_scale_percent") or 100))),
    }
    return {
        "ok": True,
        "id": str(row["id"]),
        "slug": str(row["slug"]),
        "name": str(row["name"] or "NextToppers QR"),
        "qr_type": str(row["qr_type"] or "url"),
        "tracking_mode": str(row["tracking_mode"] or "tracked"),
        "identity_mode": str(row["identity_mode"] or "anonymous"),
        "target_url": target,
        "experience": safe_experience,
        "updated_at": str(row["updated_at"] or ""),
    }


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
