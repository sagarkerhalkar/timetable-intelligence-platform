from __future__ import annotations

import base64
import csv
import io
import json
import math
import re
import secrets
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

import time as perf_time
from difflib import SequenceMatcher
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import settings
from ..database import Database
from ..dependencies import get_database, get_sync_service
from ..models import (
    ChangeField,
    ChangeRecord,
    ChangeSummary,
    ContentSearchResponse,
    DashboardSummary,
    NotificationDelivery,
    NotificationRule,
    NotificationStatus,
    NotificationTestResponse,
    PaginatedResponse,
    QrAnalyticsSummary,
    QrAssetResponse,
    QrCodeCreate,
    QrCodeRecord,
    QrCodeUpdate,
    QrBulkCreateRequest,
    QrBulkCreateResponse,
    QrTemplateCreate,
    QrTemplateRecord,
    QrTemplateUpdate,
    QrPreviewRequest,
    QrResolveResponse,
    QrScanConfirm,
    SheetSource,
    SourceAnalysisSummary,
    SourceCreate,
    TestCycleSummary,
    TestDataQuality,
    TestMonitorResponse,
    TestMonitorSummary,
    TestNotificationPresetRequest,
    TestRecord,
    TestStatusBucket,
    WorkbookProfile,
    SyncResult,
    SyncStartResponse,
)
from ..services.exports import build_timetable_pdf, build_timetable_xlsx
from ..services.google_sheets import InvalidGoogleSheetUrl, extract_spreadsheet_id
from ..services.notifications import NotificationService
from ..services.qr_edge_runtime import QrEdgeSyncError, deactivate_qr_record, sync_qr_record, sync_qr_records
from ..services.test_series import status_is_done, test_is_due, tests_for_sunday, weekly_cycle
from ..services.sync_service import SyncService
from ..timezones import INDIA_TIMEZONE
from ..utils import normalize_search_text, stable_hash

router = APIRouter(prefix="/api/v1")


_TEST_MONITOR_CACHE_TTL_SECONDS = 45.0
_TEST_MONITOR_CACHE: dict[tuple[str, str, bool], tuple[float, TestMonitorResponse]] = {}
_TEST_MONITOR_CACHE_LOCK = Lock()
_TEST_MONITOR_WARM_UNTIL: dict[str, float] = {}


def _test_monitor_cache_get(key: tuple[str, str, bool]) -> TestMonitorResponse | None:
    now = perf_time.monotonic()
    with _TEST_MONITOR_CACHE_LOCK:
        cached = _TEST_MONITOR_CACHE.get(key)
        if cached is None:
            return None
        created_at, response = cached
        if now - created_at > _TEST_MONITOR_CACHE_TTL_SECONDS:
            _TEST_MONITOR_CACHE.pop(key, None)
            return None
        return response


def _test_monitor_cache_put(key: tuple[str, str, bool], response: TestMonitorResponse) -> TestMonitorResponse:
    with _TEST_MONITOR_CACHE_LOCK:
        _TEST_MONITOR_CACHE[key] = (perf_time.monotonic(), response)
        if len(_TEST_MONITOR_CACHE) > 48:
            oldest = sorted(_TEST_MONITOR_CACHE.items(), key=lambda pair: pair[1][0])[:12]
            for stale_key, _ in oldest:
                _TEST_MONITOR_CACHE.pop(stale_key, None)
    return response


def _warm_test_monitor_tabs(database: Database, source_id: str, sheet_names: list[str]) -> None:
    # Run after the lightweight tab-count response has already been returned.
    # One sequential warm pass avoids a CPU spike while making the user's first tab click fast.
    for sheet_name in sheet_names[:16]:
        try:
            test_monitor(source_id=source_id, sheet_name=sheet_name, compact=True, database=database)
        except Exception:
            continue


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "time": datetime.now(UTC).isoformat(),
    }



_QR_SOURCE_TAGS = {
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "instagram": "Instagram",
    "google-chat": "Google Chat",
    "google_chat": "Google Chat",
    "web": "Web / Website",
    "website": "Web / Website",
    "facebook": "Facebook",
    "messenger": "Messenger",
    "linkedin": "LinkedIn",
    "x": "X / Twitter",
    "twitter": "X / Twitter",
    "email": "Email",
    "teams": "Microsoft Teams",
    "slack": "Slack",
    "discord": "Discord",
}


def _normalized_qr_source_tag(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9_-]+", "-", value.casefold()).strip("-_")[:32]
    return normalized if normalized in _QR_SOURCE_TAGS else None


def _qr_tracking_url(code: QrCodeRecord, source_tag: str | None = None) -> str:
    base_url = (code.public_base_url or settings.qr_public_base_url).rstrip("/")
    url = f"{base_url}/q/{code.slug}"
    normalized = _normalized_qr_source_tag(source_tag)
    return f"{url}?src={normalized}" if normalized else url


def _automatic_qr_name(target_url: str, qr_type: str = "url", content: dict[str, object] | None = None) -> str:
    content = content or {}
    labels = {
        "calendar": "Calendar Event", "contact": "Contact", "email": "Email",
        "geo": "Location", "phone": "Phone", "wifi": "Wi-Fi Network",
    }
    if qr_type == "url":
        parsed = urlparse(target_url)
        host = (parsed.hostname or "Link").removeprefix("www.")
        label = "Google Form" if host == "forms.gle" or (
            host == "docs.google.com" and parsed.path.casefold().startswith("/forms/")
        ) else (host or "Link")
    else:
        label = str(content.get("title") or content.get("full_name") or content.get("ssid") or labels.get(qr_type, "QR"))
    stamp = datetime.now(INDIA_TIMEZONE).strftime("%d %b %Y · %I:%M %p")
    return f"{label} · {stamp}"[:120]


def _clean_text(value: object, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:limit]


def _clean_email(value: object) -> str:
    email = _clean_text(value, 254).casefold()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return email


def _clean_phone(value: object) -> str:
    phone = _clean_text(value, 40)
    if not phone or not re.fullmatch(r"[+0-9()\- .]{5,40}", phone):
        raise HTTPException(status_code=422, detail="Enter a valid phone number.")
    return phone


def _validate_qr_content(qr_type: str, content: dict[str, object], target_url: str | None = None) -> tuple[str, dict[str, object]]:
    data = dict(content or {})
    if qr_type == "url":
        url = _clean_text(data.get("url") or target_url, 2000)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=422, detail="Enter a complete http:// or https:// URL.")
        return url, {"url": url}
    if qr_type == "calendar":
        title = _clean_text(data.get("title"), 160)
        start = _clean_text(data.get("start"), 64)
        end = _clean_text(data.get("end"), 64)
        if not title or not start:
            raise HTTPException(status_code=422, detail="Calendar event needs a title and start date/time.")
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if end:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if end_dt <= start_dt:
                    raise ValueError
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Calendar date/time is invalid. End must be after start.") from exc
        normalized = {
            "title": title, "start": start, "end": end,
            "timezone": _clean_text(data.get("timezone") or "Asia/Kolkata", 80),
            "location": _clean_text(data.get("location"), 240),
            "description": _clean_text(data.get("description"), 1200),
        }
        return "urn:tti:calendar", normalized
    if qr_type == "contact":
        full_name = _clean_text(data.get("full_name"), 160)
        if not full_name:
            raise HTTPException(status_code=422, detail="Contact QR needs a name.")
        email = _clean_text(data.get("email"), 254)
        if email:
            email = _clean_email(email)
        phone = _clean_text(data.get("phone"), 40)
        if phone:
            phone = _clean_phone(phone)
        website = _clean_text(data.get("website"), 1000)
        if website:
            parsed = urlparse(website)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise HTTPException(status_code=422, detail="Contact website must be a complete http:// or https:// URL.")
        normalized = {
            "full_name": full_name, "company": _clean_text(data.get("company"), 160),
            "job_title": _clean_text(data.get("job_title"), 160), "phone": phone,
            "email": email, "website": website, "address": _clean_text(data.get("address"), 400),
        }
        return "urn:tti:contact", normalized
    if qr_type == "email":
        email = _clean_email(data.get("email"))
        subject = _clean_text(data.get("subject"), 240)
        body = _clean_text(data.get("body"), 1500)
        return f"mailto:{email}", {"email": email, "subject": subject, "body": body}
    if qr_type == "geo":
        try:
            latitude = float(data.get("latitude"))
            longitude = float(data.get("longitude"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Location needs valid latitude and longitude.") from exc
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise HTTPException(status_code=422, detail="Latitude or longitude is outside the valid range.")
        label = _clean_text(data.get("label"), 160)
        maps = f"https://www.google.com/maps/search/?api=1&query={latitude:.7f},{longitude:.7f}"
        return maps, {"latitude": latitude, "longitude": longitude, "label": label}
    if qr_type == "phone":
        phone = _clean_phone(data.get("phone"))
        return f"tel:{phone}", {"phone": phone}
    if qr_type == "wifi":
        ssid = _clean_text(data.get("ssid"), 64)
        if not ssid:
            raise HTTPException(status_code=422, detail="Wi-Fi QR needs the network name (SSID).")
        security = _clean_text(data.get("security") or "WPA", 16).upper()
        if security not in {"WPA", "WEP", "NOPASS"}:
            security = "WPA"
        password = str(data.get("password") or "")[:128]
        if security != "NOPASS" and not password:
            raise HTTPException(status_code=422, detail="Enter the Wi-Fi password or choose Open network.")
        return "urn:tti:wifi", {"ssid": ssid, "security": security, "password": password, "hidden": bool(data.get("hidden"))}
    raise HTTPException(status_code=422, detail="Unsupported QR type.")


def _wifi_escape(value: object) -> str:
    return re.sub(r'([\\;,:"])', r'\\\1', str(value or ""))


def _calendar_ics(content: dict[str, object], slug: str) -> str:
    def esc(value: object) -> str:
        return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    start = datetime.fromisoformat(str(content.get("start") or "").replace("Z", "+00:00"))
    end_raw = str(content.get("end") or "")
    end = datetime.fromisoformat(end_raw.replace("Z", "+00:00")) if end_raw else start + timedelta(hours=1)
    def stamp(dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.strftime("%Y%m%dT%H%M%S")
        return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NextToppers//QR Studio//EN", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT", f"UID:{slug}@nexttoppers.sagarkerhalkar.com", f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{stamp(start)}", f"DTEND:{stamp(end)}", f"SUMMARY:{esc(content.get('title'))}",
        f"LOCATION:{esc(content.get('location'))}", f"DESCRIPTION:{esc(content.get('description'))}",
        "END:VEVENT", "END:VCALENDAR", ""
    ])


def _contact_vcard(content: dict[str, object]) -> str:
    def esc(value: object) -> str:
        return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{esc(content.get('full_name'))}"]
    if content.get("company"): lines.append(f"ORG:{esc(content.get('company'))}")
    if content.get("job_title"): lines.append(f"TITLE:{esc(content.get('job_title'))}")
    if content.get("phone"): lines.append(f"TEL;TYPE=CELL:{esc(content.get('phone'))}")
    if content.get("email"): lines.append(f"EMAIL:{esc(content.get('email'))}")
    if content.get("website"): lines.append(f"URL:{esc(content.get('website'))}")
    if content.get("address"): lines.append(f"ADR;TYPE=WORK:;;{esc(content.get('address'))};;;;")
    lines += ["END:VCARD", ""]
    return "\r\n".join(lines)


def _direct_qr_payload(code: QrCodeRecord) -> str:
    c = code.content
    if code.qr_type == "url": return str(c.get("url") or code.target_url)
    if code.qr_type == "calendar": return _calendar_ics(c, code.slug)
    if code.qr_type == "contact": return _contact_vcard(c)
    if code.qr_type == "email":
        return "mailto:" + str(c.get("email") or "") + "?" + urlencode({k: str(c.get(k) or "") for k in ("subject", "body") if c.get(k)})
    if code.qr_type == "geo": return f"geo:{c.get('latitude')},{c.get('longitude')}?q={quote(str(c.get('label') or 'Location'))}"
    if code.qr_type == "phone": return f"tel:{c.get('phone') or ''}"
    if code.qr_type == "wifi":
        return f"WIFI:T:{_wifi_escape(c.get('security') or 'WPA')};S:{_wifi_escape(c.get('ssid'))};P:{_wifi_escape(c.get('password'))};H:{'true' if c.get('hidden') else 'false'};;"
    return code.target_url


def _qr_action(code: QrCodeRecord) -> tuple[str, str | None, dict[str, object] | None]:
    c = code.content
    if code.qr_type == "url": return "redirect", str(c.get("url") or code.target_url), None
    if code.qr_type == "email":
        url = "mailto:" + str(c.get("email") or "")
        params = {k: str(c.get(k) or "") for k in ("subject", "body") if c.get(k)}
        return "redirect", url + (("?" + urlencode(params)) if params else ""), None
    if code.qr_type == "phone": return "redirect", f"tel:{c.get('phone') or ''}", None
    if code.qr_type == "geo":
        return "redirect", f"https://www.google.com/maps/search/?api=1&query={c.get('latitude')},{c.get('longitude')}", None
    if code.qr_type in {"calendar", "contact"}: return "download", f"/backend/api/v1/qr/action/{code.slug}", None
    if code.qr_type == "wifi": return "wifi", None, c
    return "redirect", code.target_url, None

def _qr_client_profile(request: Request) -> tuple[str, str, str, str]:
    country = (
        request.headers.get("cf-ipcountry")
        or request.headers.get("x-vercel-ip-country")
        or request.headers.get("cloudfront-viewer-country")
        or request.headers.get("x-country-code")
        or "Unknown"
    ).strip().upper()[:32] or "Unknown"
    ua = (request.headers.get("user-agent") or "").casefold()

    bot_tokens = (
        "bot", "crawler", "spider", "preview", "facebookexternalhit", "telegrambot",
        "whatsapp/", "slackbot", "discordbot", "linkedinbot", "twitterbot",
        "skypeuripreview", "headlesschrome", "curl/", "wget/", "python-requests", "httpx/"
    )
    if any(token in ua for token in bot_tokens):
        device = "bot"
    elif "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        device = "Tablet"
    elif any(token in ua for token in ("mobile", "iphone", "ipod")):
        device = "Mobile"
    else:
        device = "Desktop"

    if "instagram" in ua:
        browser = "Instagram In-App"
    elif "fban/" in ua or "fbav/" in ua or "fb_iab" in ua:
        browser = "Facebook In-App"
    elif "samsungbrowser/" in ua:
        browser = "Samsung Internet"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "edg/" in ua or "edgios/" in ua or "edga/" in ua:
        browser = "Edge"
    elif "firefox/" in ua or "fxios/" in ua:
        browser = "Firefox"
    elif "chrome/" in ua or "crios/" in ua:
        browser = "Chrome"
    elif "safari/" in ua:
        browser = "Safari"
    else:
        browser = "Other"

    if "android" in ua:
        operating_system = "Android"
    elif any(token in ua for token in ("iphone", "ipad", "ipod")):
        operating_system = "iOS / iPadOS"
    elif "windows" in ua:
        operating_system = "Windows"
    elif "cros" in ua:
        operating_system = "ChromeOS"
    elif "mac os x" in ua or "macintosh" in ua:
        operating_system = "macOS"
    elif "linux" in ua:
        operating_system = "Linux"
    else:
        operating_system = "Other"
    return country, device, browser, operating_system


def _qr_source_platform(source_tag: str | None, referrer: str | None, user_agent: str) -> tuple[str, str, str]:
    normalized = _normalized_qr_source_tag(source_tag)
    referrer_host = ""
    if referrer:
        try:
            referrer_host = (urlparse(referrer).hostname or "").casefold().removeprefix("www.")[:160]
        except ValueError:
            referrer_host = ""

    if normalized:
        return _QR_SOURCE_TAGS[normalized], "tagged", referrer_host

    host_rules = (
        ("web.whatsapp.com", "WhatsApp"),
        ("whatsapp.com", "WhatsApp"),
        ("wa.me", "WhatsApp"),
        ("t.me", "Telegram"),
        ("telegram.me", "Telegram"),
        ("instagram.com", "Instagram"),
        ("chat.google.com", "Google Chat"),
        ("facebook.com", "Facebook"),
        ("messenger.com", "Messenger"),
        ("linkedin.com", "LinkedIn"),
        ("twitter.com", "X / Twitter"),
        ("x.com", "X / Twitter"),
        ("teams.microsoft.com", "Microsoft Teams"),
        ("slack.com", "Slack"),
        ("discord.com", "Discord"),
        ("mail.google.com", "Email"),
        ("outlook.live.com", "Email"),
    )
    for token, platform in host_rules:
        if token in referrer_host:
            return platform, "detected", referrer_host

    ua = user_agent.casefold()
    ua_rules = (
        ("instagram", "Instagram"),
        ("fban/", "Facebook"),
        ("fbav/", "Facebook"),
        ("telegram", "Telegram"),
        ("linkedinapp", "LinkedIn"),
        ("twitter", "X / Twitter"),
        ("teamsmobile", "Microsoft Teams"),
        ("slack", "Slack"),
        ("discord", "Discord"),
    )
    for token, platform in ua_rules:
        if token in ua:
            return platform, "detected", referrer_host

    if referrer_host:
        return "Web / Website", "detected", referrer_host
    return "Direct / QR", "unknown", referrer_host


_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_QR_ASSET_ID = re.compile(r"^[a-f0-9]{24}$")


def _safe_color(value: str, fallback: str) -> str:
    return value if _HEX_COLOR.fullmatch(value or "") else fallback


def _qr_asset_dir(database: Database) -> Path:
    path = database.path.parent / "qr_assets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _qr_asset_path(database: Database, asset_id: str | None) -> Path | None:
    if not asset_id or not _QR_ASSET_ID.fullmatch(asset_id):
        return None
    path = _qr_asset_dir(database) / f"{asset_id}.png"
    return path if path.exists() else None


def _delete_qr_asset(database: Database, asset_id: str | None) -> None:
    path = _qr_asset_path(database, asset_id)
    if path:
        path.unlink(missing_ok=True)


def _delete_qr_asset_if_unreferenced(database: Database, asset_id: str | None) -> None:
    if not asset_id:
        return
    if database.qr_asset_reference_count(asset_id) > 0:
        return
    _delete_qr_asset(database, asset_id)



def _qr_finder_origins(count: int, border: int = 4) -> list[tuple[int, int]]:
    offset = border
    far = count - border - 7
    return [(offset, offset), (far, offset), (offset, far)]


def _inside_qr_finder(row: int, column: int, count: int, border: int = 4) -> bool:
    return any(
        origin_x <= column < origin_x + 7 and origin_y <= row < origin_y + 7
        for origin_x, origin_y in _qr_finder_origins(count, border)
    )


def _svg_shape(style: str, x: float, y: float, size: float, color: str, *, center: bool = False) -> str:
    if style in {"dots", "circle"}:
        radius = size * (0.43 if not center else 0.5)
        return f'<circle cx="{x + size/2:.2f}" cy="{y + size/2:.2f}" r="{radius:.2f}" fill="{color}"/>'
    if style == "rounded":
        inset = size * (0.05 if not center else 0)
        draw_size = size - inset * 2
        return (
            f'<rect x="{x+inset:.2f}" y="{y+inset:.2f}" width="{draw_size:.2f}" height="{draw_size:.2f}" '
            f'rx="{draw_size*0.32:.2f}" fill="{color}"/>'
        )
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{size:.2f}" height="{size:.2f}" fill="{color}"/>'


def _svg_finder(
    origin_x: float,
    origin_y: float,
    unit: float,
    foreground: str,
    background: str,
    border_style: str,
    center_style: str,
) -> str:
    size = unit * 7
    x = origin_x * unit
    y = origin_y * unit
    if border_style == "circle":
        outer = f'<circle cx="{x+size/2:.2f}" cy="{y+size/2:.2f}" r="{size/2:.2f}" fill="{foreground}"/>'
        inner = f'<circle cx="{x+size/2:.2f}" cy="{y+size/2:.2f}" r="{unit*2.5:.2f}" fill="{background}"/>'
    else:
        radius = 0 if border_style == "square" else unit * 1.65
        inner_radius = 0 if border_style == "square" else unit * 1.12
        outer = f'<rect x="{x:.2f}" y="{y:.2f}" width="{size:.2f}" height="{size:.2f}" rx="{radius:.2f}" fill="{foreground}"/>'
        inner = (
            f'<rect x="{x+unit:.2f}" y="{y+unit:.2f}" width="{unit*5:.2f}" height="{unit*5:.2f}" '
            f'rx="{inner_radius:.2f}" fill="{background}"/>'
        )
    center = _svg_shape(center_style, x + unit * 2, y + unit * 2, unit * 3, foreground, center=True)
    return outer + inner + center


def _qr_matrix_svg(
    tracking_url: str,
    foreground: str,
    background: str,
    *,
    logo_data: bytes | None = None,
    frame_text: str | None = None,
    dot_style: str = "rounded",
    marker_border_style: str = "rounded",
    marker_center_style: str = "square",
    logo_scale_percent: int = 18,
    logo_background: bool = True,
    frame_style: str = "text",
) -> bytes:
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_H
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="QR image dependency is not installed.") from exc

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=1, border=4)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    count = len(matrix)
    unit = 10.0
    qr_size = count * unit

    effective_frame = frame_style if frame_style in {"none", "text", "badge"} else "text"
    visible_frame_text = frame_text if effective_frame != "none" else None
    footer = 78 if visible_frame_text else 0
    total_h = qr_size + footer

    dot_style = dot_style if dot_style in {"square", "rounded", "dots"} else "rounded"
    marker_border_style = marker_border_style if marker_border_style in {"square", "rounded", "circle"} else "rounded"
    marker_center_style = marker_center_style if marker_center_style in {"square", "rounded", "circle"} else "square"

    shapes: list[str] = []
    for row_index, row in enumerate(matrix):
        for col_index, dark in enumerate(row):
            if not dark:
                continue
            x = col_index * unit
            y = row_index * unit
            if _inside_qr_finder(row_index, col_index, count):
                eye_style = "dots" if marker_border_style == "circle" else marker_border_style
                if eye_style == "dots":
                    shapes.append(
                        f'<circle cx="{x + unit/2:.2f}" cy="{y + unit/2:.2f}" r="{unit/2:.2f}" fill="{foreground}"/>'
                    )
                elif eye_style == "rounded":
                    shapes.append(
                        f'<rect x="{x:.2f}" y="{y:.2f}" width="{unit:.2f}" height="{unit:.2f}" rx="{unit/2:.2f}" fill="{foreground}"/>'
                    )
                else:
                    shapes.append(_svg_shape("square", x, y, unit, foreground))
                continue
            if dot_style == "dots":
                size = unit * 0.82
                offset = (unit - size) / 2
                shapes.append(_svg_shape("dots", x + offset, y + offset, size, foreground))
            elif dot_style == "rounded":
                size = unit * 0.94
                offset = (unit - size) / 2
                shapes.append(_svg_shape("rounded", x + offset, y + offset, size, foreground))
            else:
                shapes.append(_svg_shape("square", x, y, unit, foreground))

    # A solid 3x3 finder center gives the center its own visual style while the
    # surrounding eye modules retain scan-safe geometry.
    centers = "".join(
        _svg_shape(
            marker_center_style,
            (origin_x + 2) * unit,
            (origin_y + 2) * unit,
            unit * 3,
            foreground,
            center=True,
        )
        for origin_x, origin_y in _qr_finder_origins(count)
    )

    logo = ""
    if logo_data:
        encoded = base64.b64encode(logo_data).decode("ascii")
        safe_percent = max(8, min(int(logo_scale_percent or 18), 28))
        logo_size = max(42, int(qr_size * safe_percent / 100))
        logo_x = (qr_size - logo_size) / 2
        logo_y = (qr_size - logo_size) / 2
        pad = max(6, int(qr_size * 0.016))
        plate = ""
        if logo_background:
            plate = (
                f'<rect x="{logo_x-pad:.2f}" y="{logo_y-pad:.2f}" width="{logo_size+pad*2:.2f}" '
                f'height="{logo_size+pad*2:.2f}" rx="{max(10,pad*1.4):.2f}" fill="{background}"/>'
            )
        logo = (
            plate
            + f'<image href="data:image/png;base64,{encoded}" x="{logo_x:.2f}" y="{logo_y:.2f}" '
              f'width="{logo_size:.2f}" height="{logo_size:.2f}" preserveAspectRatio="xMidYMid meet"/>'
        )

    footer_svg = ""
    if visible_frame_text:
        safe = (
            visible_frame_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;")
        )
        if effective_frame == "badge":
            badge_width = min(qr_size - 32, max(170, len(safe) * 17 + 52))
            badge_x = (qr_size - badge_width) / 2
            footer_svg = (
                f'<rect x="{badge_x:.2f}" y="{qr_size+16:.2f}" width="{badge_width:.2f}" height="48" '
                f'rx="24" fill="{foreground}"/>'
                f'<text x="{qr_size/2:.2f}" y="{qr_size+48:.2f}" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="{background}">{safe}</text>'
            )
        else:
            footer_svg = (
                f'<text x="{qr_size/2:.2f}" y="{qr_size+45:.2f}" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="{foreground}">{safe}</text>'
            )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{qr_size:.0f}" height="{total_h:.0f}" '
        f'viewBox="0 0 {qr_size:.0f} {total_h:.0f}">'
        f'<rect width="100%" height="100%" fill="{background}"/>'
        f'{"".join(shapes)}{centers}{logo}{footer_svg}</svg>'
    )
    return svg.encode("utf-8")

def _pil_draw_marker(
    draw: object,
    origin_x: int,
    origin_y: int,
    unit: int,
    foreground: str,
    background: str,
    border_style: str,
    center_style: str,
) -> None:
    x = origin_x * unit
    y = origin_y * unit
    outer_box = (x, y, x + unit * 7 - 1, y + unit * 7 - 1)
    inner_box = (x + unit, y + unit, x + unit * 6 - 1, y + unit * 6 - 1)
    center_box = (x + unit * 2, y + unit * 2, x + unit * 5 - 1, y + unit * 5 - 1)

    # Clear the full finder footprint first so circle/rounded eye styles do not
    # inherit dark pixels from the underlying styled renderer.
    draw.rectangle(outer_box, fill=background)

    if border_style == "circle":
        draw.ellipse(outer_box, fill=foreground)
        draw.ellipse(inner_box, fill=background)
    elif border_style == "rounded":
        draw.rounded_rectangle(outer_box, radius=max(2, int(unit * 1.65)), fill=foreground)
        draw.rounded_rectangle(inner_box, radius=max(2, int(unit * 1.1)), fill=background)
    else:
        draw.rectangle(outer_box, fill=foreground)
        draw.rectangle(inner_box, fill=background)

    if center_style == "circle":
        draw.ellipse(center_box, fill=foreground)
    elif center_style == "rounded":
        draw.rounded_rectangle(center_box, radius=max(2, int(unit * 0.85)), fill=foreground)
    else:
        draw.rectangle(center_box, fill=foreground)


def _render_qr_png(
    tracking_url: str,
    code_design: dict[str, object],
    database: Database,
) -> bytes:
    try:
        import qrcode
        from PIL import Image, ImageDraw, ImageFont
        from qrcode.constants import ERROR_CORRECT_H
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.colormasks import SolidFillColorMask
        from qrcode.image.styles.moduledrawers.pil import CircleModuleDrawer, RoundedModuleDrawer, SquareModuleDrawer
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="QR image dependency is not installed.") from exc

    foreground = _safe_color(str(code_design.get("foreground_color") or ""), "#111827")
    background = _safe_color(str(code_design.get("background_color") or ""), "#FFFFFF")
    dot_style = str(code_design.get("dot_style") or "rounded")
    marker_border_style = str(code_design.get("marker_border_style") or "rounded")
    marker_center_style = str(code_design.get("marker_center_style") or "square")
    marker_border_color = _safe_color(str(code_design.get("marker_border_color") or ""), foreground)
    marker_center_color = _safe_color(str(code_design.get("marker_center_color") or ""), foreground)
    frame_style = str(code_design.get("frame_style") or "text")
    logo_scale_percent = max(8, min(int(code_design.get("logo_scale_percent") or 18), 28))
    logo_background = bool(code_design.get("logo_background", True))

    def rgb(value: str) -> tuple[int, int, int]:
        return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]

    module_drawer = {
        "square": SquareModuleDrawer,
        "rounded": RoundedModuleDrawer,
        "dots": CircleModuleDrawer,
    }.get(dot_style, RoundedModuleDrawer)()
    eye_drawer = {
        "square": SquareModuleDrawer,
        "rounded": RoundedModuleDrawer,
        "circle": CircleModuleDrawer,
    }.get(marker_border_style, RoundedModuleDrawer)()

    box_size = 12
    border = 4
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=box_size, border=border)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    styled = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        eye_drawer=eye_drawer,
        color_mask=SolidFillColorMask(back_color=rgb(background), front_color=rgb(foreground)),
    )
    image = styled.convert("RGBA")

    # Draw the three finder markers ourselves so border shape/color and
    # center shape/color are truly independent, matching commercial QR editors.
    draw = ImageDraw.Draw(image)
    full_module_count = qr.modules_count + border * 2
    for origin_x, origin_y in _qr_finder_origins(full_module_count, border):
        _pil_draw_marker(
            draw,
            origin_x,
            origin_y,
            box_size,
            marker_border_color,
            background,
            marker_border_style,
            marker_center_style,
        )
        # Repaint the 3x3 center with its own color after drawing the border.
        left = (origin_x + 2) * box_size
        top = (origin_y + 2) * box_size
        center_box = (left, top, left + box_size * 3 - 1, top + box_size * 3 - 1)
        if marker_center_style == "circle":
            draw.ellipse(center_box, fill=marker_center_color)
        elif marker_center_style == "rounded":
            draw.rounded_rectangle(center_box, radius=max(3, int(box_size * 0.7)), fill=marker_center_color)
        else:
            draw.rectangle(center_box, fill=marker_center_color)

    logo_path = _qr_asset_path(database, str(code_design.get("logo_asset_id") or ""))
    if logo_path:
        with Image.open(logo_path) as source:
            logo = source.convert("RGBA")
            max_side = max(48, int(image.width * logo_scale_percent / 100))
            logo.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            if logo_background:
                pad = max(7, int(image.width * 0.016))
                plate = Image.new("RGBA", (logo.width + pad * 2, logo.height + pad * 2), background)
                mask = Image.new("L", plate.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle((0, 0, plate.width, plate.height), radius=max(8, pad), fill=255)
                plate.putalpha(mask)
                plate.alpha_composite(logo, (pad, pad))
                image.alpha_composite(plate, ((image.width - plate.width) // 2, (image.height - plate.height) // 2))
            else:
                image.alpha_composite(logo, ((image.width - logo.width) // 2, (image.height - logo.height) // 2))

    frame_text = str(code_design.get("frame_text") or "").strip()
    if frame_style != "none" and frame_text:
        footer_h = 92
        framed = Image.new("RGBA", (image.width, image.height + footer_h), background)
        framed.alpha_composite(image, (0, 0))
        footer_draw = ImageDraw.Draw(framed)
        try:
            font = ImageFont.truetype("arialbd.ttf", 30)
        except OSError:
            font = ImageFont.load_default()
        text = frame_text[:42]
        bbox = footer_draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if frame_style == "badge":
            pad_x = 24
            badge_w = min(framed.width - 30, max(text_w + pad_x * 2, 170))
            left = (framed.width - badge_w) // 2
            top = image.height + 18
            footer_draw.rounded_rectangle((left, top, left + badge_w, top + 52), radius=26, fill=foreground)
            footer_draw.text(((framed.width - text_w) // 2, top + (52 - text_h) // 2 - bbox[1]), text, fill=background, font=font)
        else:
            footer_draw.text(((framed.width - text_w) // 2, image.height + 28 - bbox[1]), text, fill=foreground, font=font)
        image = framed

    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()

def _record_legacy_qr_scan(code: QrCodeRecord, request: Request, database: Database) -> tuple[str, bool]:
    """Compatibility path for old direct redirect URLs.

    These hits are deliberately marked unconfirmed so the v1.0.20 main statistics
    are not polluted by link preview bots or server-side fetches.
    """
    visitor_token = request.cookies.get("tti_qr_visitor")
    is_new_visitor = not visitor_token
    if not visitor_token:
        visitor_token = secrets.token_urlsafe(18)
    visitor_hash = stable_hash("qr-visitor", visitor_token)
    country, device, browser, operating_system = _qr_client_profile(request)
    database.record_qr_scan(
        qr_id=code.id,
        scanned_at=datetime.now(UTC),
        visitor_hash=visitor_hash,
        country=country,
        device_type=device,
        browser=browser,
        operating_system=operating_system,
        platform="Direct / QR",
        source_confidence="legacy",
        event_hash=None,
        confirmed=False,
    )
    return visitor_token, is_new_visitor


def _set_qr_visitor_cookie(response: Response, request: Request, visitor_token: str, is_new_visitor: bool = True) -> None:
    if not is_new_visitor:
        return
    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).casefold()
    response.set_cookie(
        "tti_qr_visitor",
        visitor_token,
        max_age=31536000,
        httponly=True,
        samesite="lax",
        secure=forwarded_proto == "https",
    )


@router.post("/qr-assets", response_model=QrAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_qr_asset(
    file: UploadFile = File(...),
    database: Database = Depends(get_database),
) -> QrAssetResponse:
    content_type = (file.content_type or "").casefold()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=422, detail="Upload a PNG, JPG or WEBP image.")
    raw = await file.read(6 * 1024 * 1024 + 1)
    if len(raw) > 6 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is too large. Maximum size is 6 MB.")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as source:
            source.load()
            image = source.convert("RGBA")
            image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
            width, height = image.size
            asset_id = secrets.token_hex(12)
            destination = _qr_asset_dir(database) / f"{asset_id}.png"
            image.save(destination, format="PNG", optimize=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="The uploaded image could not be read.") from exc
    return QrAssetResponse(
        id=asset_id,
        url=f"/api/v1/qr-assets/{asset_id}",
        width=width,
        height=height,
    )


@router.get("/qr-assets/{asset_id}")
def get_qr_asset(asset_id: str, database: Database = Depends(get_database)) -> Response:
    path = _qr_asset_path(database, asset_id)
    if path is None:
        raise HTTPException(status_code=404, detail="QR asset not found")
    return Response(content=path.read_bytes(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/qr-preview")
def qr_preview(payload: QrPreviewRequest, database: Database = Depends(get_database)) -> Response:
    preview_url = f"{settings.qr_public_base_url.rstrip('/')}/q/preview"
    png = _render_qr_png(preview_url, payload.design.model_dump(), database)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


def _clean_template_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _ensure_template_name_available(database: Database, name: str, exclude_id: str | None = None) -> None:
    needle = name.casefold()
    for template in database.list_qr_templates():
        if template.id != exclude_id and template.name.casefold() == needle:
            raise HTTPException(status_code=409, detail="A QR template with this name already exists.")


@router.get("/qr-templates", response_model=list[QrTemplateRecord])
def list_qr_templates(database: Database = Depends(get_database)) -> list[QrTemplateRecord]:
    return database.list_qr_templates()


@router.get("/qr-templates/{template_id}", response_model=QrTemplateRecord)
def get_qr_template(template_id: str, database: Database = Depends(get_database)) -> QrTemplateRecord:
    template = database.get_qr_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    return template


@router.post("/qr-templates", response_model=QrTemplateRecord, status_code=status.HTTP_201_CREATED)
def create_qr_template(payload: QrTemplateCreate, database: Database = Depends(get_database)) -> QrTemplateRecord:
    if payload.identity_mode == "email" and payload.tracking_mode != "tracked":
        raise HTTPException(status_code=422, detail="Email identification requires Tracked mode.")
    clean_name = _clean_template_name(payload.name)
    _ensure_template_name_available(database, clean_name)
    return database.create_qr_template(
        template_id=secrets.token_hex(12), name=clean_name, description=payload.description.strip(),
        tracking_mode=payload.tracking_mode, identity_mode=payload.identity_mode,
        design_json=json.dumps(payload.design.model_dump(), ensure_ascii=False),
        experience_json=json.dumps(payload.experience.model_dump(), ensure_ascii=False),
        is_default=payload.is_default, created_at=datetime.now(UTC),
    )


@router.patch("/qr-templates/{template_id}", response_model=QrTemplateRecord)
def update_qr_template(template_id: str, payload: QrTemplateUpdate, database: Database = Depends(get_database)) -> QrTemplateRecord:
    existing = database.get_qr_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    tracking_mode = payload.tracking_mode or existing.tracking_mode
    identity_mode = payload.identity_mode or existing.identity_mode
    if identity_mode == "email" and tracking_mode != "tracked":
        raise HTTPException(status_code=422, detail="Email identification requires Tracked mode.")
    clean_name = _clean_template_name(payload.name) if payload.name is not None else None
    if clean_name is not None:
        _ensure_template_name_available(database, clean_name, template_id)
    updated = database.update_qr_template(
        template_id,
        name=clean_name, description=payload.description.strip() if payload.description is not None else None,
        tracking_mode=payload.tracking_mode, identity_mode=payload.identity_mode,
        design_json=json.dumps(payload.design.model_dump(), ensure_ascii=False) if payload.design is not None else None,
        experience_json=json.dumps(payload.experience.model_dump(), ensure_ascii=False) if payload.experience is not None else None,
        is_default=payload.is_default,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    old_assets = {existing.design.logo_asset_id, existing.experience.asset_id} - {None}
    new_assets = {updated.design.logo_asset_id, updated.experience.asset_id} - {None}
    for stale_asset in old_assets - new_assets:
        _delete_qr_asset_if_unreferenced(database, stale_asset)
    return updated


@router.post("/qr-templates/{template_id}/duplicate", response_model=QrTemplateRecord, status_code=status.HTTP_201_CREATED)
def duplicate_qr_template(template_id: str, database: Database = Depends(get_database)) -> QrTemplateRecord:
    existing = database.get_qr_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    base = f"{existing.name} Copy"
    name = base
    suffix = 2
    used = {template.name.casefold() for template in database.list_qr_templates()}
    while name.casefold() in used:
        name = f"{base} {suffix}"
        suffix += 1
    return database.create_qr_template(
        template_id=secrets.token_hex(12), name=name, description=existing.description,
        tracking_mode=existing.tracking_mode, identity_mode=existing.identity_mode,
        design_json=json.dumps(existing.design.model_dump(), ensure_ascii=False),
        experience_json=json.dumps(existing.experience.model_dump(), ensure_ascii=False),
        is_default=False, created_at=datetime.now(UTC),
    )


@router.delete("/qr-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_qr_template(template_id: str, database: Database = Depends(get_database)) -> Response:
    existing = database.get_qr_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    assets = {existing.design.logo_asset_id, existing.experience.asset_id} - {None}
    if not database.delete_qr_template(template_id):
        raise HTTPException(status_code=404, detail="QR template not found")
    for asset_id in assets:
        _delete_qr_asset_if_unreferenced(database, asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/qr-bulk", response_model=QrBulkCreateResponse, status_code=status.HTTP_201_CREATED)
def create_qr_codes_bulk(payload: QrBulkCreateRequest, database: Database = Depends(get_database)) -> QrBulkCreateResponse:
    template = database.get_qr_template(payload.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="QR template not found")
    if template.tracking_mode != "tracked":
        raise HTTPException(status_code=422, detail="Bulk QR analytics requires a Tracked template. Direct QR codes do not pass through web analytics.")
    seen_names: set[str] = set()
    records: list[dict[str, object]] = []
    reserved_slugs: set[str] = set()
    alphabet = "23456789abcdefghjkmnpqrstuvwxyz"
    stamp = datetime.now(UTC).isoformat()
    for item in payload.items:
        clean_name = re.sub(r"\s+", " ", item.name.strip())
        name_key = clean_name.casefold()
        if name_key in seen_names:
            raise HTTPException(status_code=422, detail=f"Duplicate QR name in bulk list: {clean_name}")
        seen_names.add(name_key)
        target, content = _validate_qr_content("url", {"url": str(item.url)}, str(item.url))
        slug = ""
        for _ in range(30):
            candidate = "".join(secrets.choice(alphabet) for _ in range(7))
            if candidate not in reserved_slugs and database.get_qr_code_by_slug(candidate) is None:
                slug = candidate
                reserved_slugs.add(candidate)
                break
        if not slug:
            raise HTTPException(status_code=500, detail="Could not allocate unique QR codes for this bulk request.")
        records.append({
            "id": secrets.token_hex(12), "name": clean_name, "slug": slug, "qr_type": "url",
            "tracking_mode": template.tracking_mode, "identity_mode": template.identity_mode,
            "target_url": target, "payload_json": json.dumps(content, ensure_ascii=False),
            "public_base_url": settings.qr_public_base_url,
            "design_json": json.dumps(template.design.model_dump(), ensure_ascii=False),
            "experience_json": json.dumps(template.experience.model_dump(), ensure_ascii=False),
            "template_id": template.id, "created_at": stamp,
        })
    created = database.create_qr_codes_bulk(records)
    if len(created) != len(records):
        raise HTTPException(status_code=500, detail="Bulk QR creation did not complete.")
    try:
        sync_qr_records(created)
    except QrEdgeSyncError as exc:
        for code in created:
            try:
                deactivate_qr_record(code)
            except Exception:
                pass
            try:
                database.delete_qr_code(code.id)
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=f"Cloudflare QR sync failed; bulk QR creation was rolled back: {exc}") from exc
    return QrBulkCreateResponse(template=database.get_qr_template(template.id) or template, created=created, count=len(created))


@router.get("/qr-codes", response_model=list[QrCodeRecord])
def list_qr_codes(database: Database = Depends(get_database)) -> list[QrCodeRecord]:
    return database.list_qr_codes()


@router.get("/qr-codes/{qr_id}", response_model=QrCodeRecord)
def get_qr_code(qr_id: str, database: Database = Depends(get_database)) -> QrCodeRecord:
    code = database.get_qr_code(qr_id)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    return code


@router.post("/qr-codes", response_model=QrCodeRecord, status_code=status.HTTP_201_CREATED)
def create_qr_code(payload: QrCodeCreate, database: Database = Depends(get_database)) -> QrCodeRecord:
    raw_target = str(payload.target_url) if payload.target_url is not None else None
    target, content = _validate_qr_content(payload.qr_type, payload.content, raw_target)
    tracking_mode = payload.tracking_mode
    if payload.identity_mode == "email" and tracking_mode != "tracked":
        raise HTTPException(status_code=422, detail="Email identification requires Tracked mode.")
    clean_name = re.sub(r"\s+", " ", (payload.name or "").strip()) or _automatic_qr_name(target, payload.qr_type, content)
    alphabet = "23456789abcdefghjkmnpqrstuvwxyz"
    for _ in range(12):
        qr_id = secrets.token_hex(12)
        slug = "".join(secrets.choice(alphabet) for _ in range(7))
        if database.get_qr_code_by_slug(slug) is None:
            created = database.create_qr_code(
                qr_id=qr_id, name=clean_name, slug=slug, qr_type=payload.qr_type,
                tracking_mode=tracking_mode, identity_mode=payload.identity_mode,
                target_url=target, payload_json=json.dumps(content, ensure_ascii=False),
                public_base_url=settings.qr_public_base_url, short_url=None,
                design_json=json.dumps(payload.design.model_dump(), ensure_ascii=False),
                experience_json=json.dumps(payload.experience.model_dump(), ensure_ascii=False),
                created_at=datetime.now(UTC),
            )
            try:
                sync_qr_record(created)
            except QrEdgeSyncError as exc:
                try:
                    database.delete_qr_code(created.id)
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=f"Cloudflare QR sync failed; QR creation was rolled back: {exc}") from exc
            return created
    raise HTTPException(status_code=500, detail="Could not create a unique QR code.")


@router.patch("/qr-codes/{qr_id}", response_model=QrCodeRecord)
def update_qr_code(qr_id: str, payload: QrCodeUpdate, database: Database = Depends(get_database)) -> QrCodeRecord:
    existing = database.get_qr_code(qr_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    qr_type = payload.qr_type or existing.qr_type
    tracking_mode = payload.tracking_mode or existing.tracking_mode
    identity_mode = payload.identity_mode or existing.identity_mode
    if identity_mode == "email" and tracking_mode != "tracked":
        raise HTTPException(status_code=422, detail="Email identification requires Tracked mode.")
    target = None
    content_json = None
    if payload.content is not None or payload.target_url is not None or payload.qr_type is not None:
        raw_target = str(payload.target_url) if payload.target_url is not None else existing.target_url
        raw_content = dict(payload.content) if payload.content is not None else dict(existing.content)
        # URL QR destinations are stored in both target_url and content["url"].
        # When the caller explicitly edits target_url without sending content,
        # make that new URL canonical so stale content cannot overwrite it.
        if qr_type == "url" and payload.target_url is not None and payload.content is None:
            raw_content["url"] = raw_target
        target, content = _validate_qr_content(qr_type, raw_content, raw_target)
        content_json = json.dumps(content, ensure_ascii=False)
    name = re.sub(r"\s+", " ", (payload.name or "").strip()) if payload.name is not None else None
    if payload.name is not None and not name:
        name = _automatic_qr_name(target or existing.target_url, qr_type, payload.content or existing.content)
    updated = database.update_qr_code(
        qr_id, name=name, qr_type=qr_type if payload.qr_type is not None else None,
        tracking_mode=tracking_mode if payload.tracking_mode is not None else None,
        identity_mode=identity_mode if payload.identity_mode is not None else None,
        target_url=target, payload_json=content_json,
        design_json=json.dumps(payload.design.model_dump(), ensure_ascii=False) if payload.design is not None else None,
        experience_json=json.dumps(payload.experience.model_dump(), ensure_ascii=False) if payload.experience is not None else None,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    try:
        sync_qr_record(updated)
    except QrEdgeSyncError as exc:
        restored = database.update_qr_code(
            qr_id,
            name=existing.name,
            qr_type=existing.qr_type,
            tracking_mode=existing.tracking_mode,
            identity_mode=existing.identity_mode,
            target_url=existing.target_url,
            payload_json=json.dumps(existing.content, ensure_ascii=False),
            design_json=json.dumps(existing.design.model_dump(), ensure_ascii=False),
            experience_json=json.dumps(existing.experience.model_dump(), ensure_ascii=False),
        )
        try:
            sync_qr_record(restored or existing)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Cloudflare QR sync failed; QR edit was rolled back: {exc}") from exc
    old_assets = {existing.design.logo_asset_id, existing.experience.asset_id} - {None}
    new_assets = {updated.design.logo_asset_id, updated.experience.asset_id} - {None}
    for stale_asset in old_assets - new_assets:
        _delete_qr_asset_if_unreferenced(database, stale_asset)
    return updated


@router.post("/qr-codes/{qr_id}/active", response_model=QrCodeRecord)
def set_qr_code_active(
    qr_id: str,
    active: bool = Query(...),
    database: Database = Depends(get_database),
) -> QrCodeRecord:
    existing = database.get_qr_code(qr_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    code = database.set_qr_code_active(qr_id, active)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    try:
        sync_qr_record(code)
    except QrEdgeSyncError as exc:
        restored = database.set_qr_code_active(qr_id, existing.active)
        try:
            sync_qr_record(restored or existing)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Cloudflare QR sync failed; Active/Inactive change was rolled back: {exc}") from exc
    return code


@router.delete("/qr-codes/{qr_id}/scans")
def clear_qr_code_scans(qr_id: str, database: Database = Depends(get_database)) -> dict[str, int | str]:
    deleted = database.clear_qr_scans(qr_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    return {"qr_id": qr_id, "deleted_scans": deleted}


@router.delete("/qr-codes/{qr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_qr_code(qr_id: str, database: Database = Depends(get_database)) -> Response:
    code = database.get_qr_code(qr_id)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    try:
        deactivate_qr_record(code)
    except QrEdgeSyncError as exc:
        raise HTTPException(status_code=502, detail=f"Cloudflare QR sync failed; QR was NOT deleted: {exc}") from exc
    if not database.delete_qr_code(qr_id):
        try:
            sync_qr_record(code)
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="QR code not found")
    _delete_qr_asset_if_unreferenced(database, code.design.logo_asset_id)
    _delete_qr_asset_if_unreferenced(database, code.experience.asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/qr-codes/{qr_id}/image")
def qr_code_image(
    qr_id: str,
    format: Literal["png", "svg", "pdf"] = Query("png"),
    download: bool = Query(False),
    source: str | None = Query(None, max_length=40),
    database: Database = Depends(get_database),
) -> Response:
    code = database.get_qr_code(qr_id)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    encoded_value = _qr_tracking_url(code, source) if code.tracking_mode == "tracked" else _direct_qr_payload(code)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", code.name).strip("-") or "qr-code"
    headers = {"Cache-Control": "no-store"}
    design = code.design.model_dump()
    logo_path = _qr_asset_path(database, code.design.logo_asset_id)
    logo_data = logo_path.read_bytes() if logo_path else None

    png_content = _render_qr_png(encoded_value, design, database)

    if format == "svg":
        # Use the exact scan-verified styled QR generated for PNG inside an SVG
        # document. This preserves every dot/eye/logo/frame choice consistently
        # across download formats while avoiding SVG-renderer differences that
        # can make heavily styled finder markers unreliable on some scanners.
        try:
            from PIL import Image
            with Image.open(io.BytesIO(png_content)) as svg_source:
                svg_width, svg_height = svg_source.size
        except Exception:
            svg_width, svg_height = (720, 812)
        encoded_png = base64.b64encode(png_content).decode("ascii")
        content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" '
            f'viewBox="0 0 {svg_width} {svg_height}">'
            f'<image href="data:image/png;base64,{encoded_png}" x="0" y="0" width="{svg_width}" height="{svg_height}"/>'
            f'</svg>'
        ).encode("utf-8")
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}-qr.svg"'
        return Response(content=content, media_type="image/svg+xml", headers=headers)
    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="PDF export dependency is not installed.") from exc
        output = io.BytesIO()
        width, height = A4
        pdf = canvas.Canvas(output, pagesize=A4)
        pdf_name = code.name.encode("latin-1", "replace").decode("latin-1")
        pdf.setTitle(f"{pdf_name} QR Code")
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(width / 2, height - 72, pdf_name[:70])
        size = min(width - 120, 390)
        pdf.drawImage(
            ImageReader(io.BytesIO(png_content)),
            (width - size) / 2,
            height - 110 - size,
            size,
            size,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, height - 130 - size, f"{code.qr_type.title()} QR · {code.tracking_mode.title()} mode")
        destination = (code.target_url if code.qr_type == "url" else code.name).encode("latin-1", "replace").decode("latin-1")
        if len(destination) > 88:
            destination = destination[:85] + "..."
        pdf.setFillGray(0.35)
        pdf.drawCentredString(width / 2, height - 148 - size, destination)
        pdf.save()
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}-qr.pdf"'
        return Response(content=output.getvalue(), media_type="application/pdf", headers=headers)

    if download:
        headers["Content-Disposition"] = f'attachment; filename="{safe_name}-qr.png"'
    return Response(content=png_content, media_type="image/png", headers=headers)


@router.get("/qr/wifi/{slug}/image", include_in_schema=False)
def qr_wifi_direct_image(slug: str, database: Database = Depends(get_database)) -> Response:
    code = database.get_qr_code_by_slug(slug)
    if code is None or code.qr_type != "wifi":
        raise HTTPException(status_code=404, detail="Wi-Fi QR not found")
    png = _render_qr_png(_direct_qr_payload(code), code.design.model_dump(), database)
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/qr/resolve/{slug}", response_model=QrResolveResponse, include_in_schema=False)
def resolve_qr_code(slug: str, database: Database = Depends(get_database)) -> JSONResponse:
    code = database.get_qr_code_by_slug(slug)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not code.active:
        raise HTTPException(status_code=410, detail="This QR code is inactive")
    if code.tracking_mode != "tracked":
        raise HTTPException(status_code=409, detail="This is a direct QR and does not use the tracked scan page.")
    action_kind, action_url, wifi = _qr_action(code)
    return JSONResponse(content={
        "qr_type": code.qr_type, "action_kind": action_kind, "action_url": action_url,
        "experience": code.experience.model_dump(), "identity_mode": code.identity_mode,
        "wifi": wifi,
    }, headers={"Cache-Control": "no-store"})


@router.get("/qr/action/{slug}", include_in_schema=False)
def qr_action(slug: str, database: Database = Depends(get_database)) -> Response:
    code = database.get_qr_code_by_slug(slug)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not code.active:
        raise HTTPException(status_code=410, detail="This QR code is inactive")
    if code.qr_type == "calendar":
        body = _calendar_ics(code.content, code.slug)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", code.name).strip("-") or "event"
        return Response(body, media_type="text/calendar; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{safe}.ics"', "Cache-Control": "no-store"})
    if code.qr_type == "contact":
        body = _contact_vcard(code.content)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", code.name).strip("-") or "contact"
        return Response(body, media_type="text/vcard; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{safe}.vcf"', "Cache-Control": "no-store"})
    action_kind, action_url, _ = _qr_action(code)
    if action_kind == "redirect" and action_url:
        return RedirectResponse(action_url, status_code=302, headers={"Cache-Control": "no-store"})
    raise HTTPException(status_code=409, detail="This QR action is handled on the scan screen.")


@router.post("/qr/confirm/{slug}", include_in_schema=False)
def confirm_qr_scan(
    slug: str,
    payload: QrScanConfirm,
    request: Request,
    database: Database = Depends(get_database),
) -> JSONResponse:
    code = database.get_qr_code_by_slug(slug)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not code.active:
        raise HTTPException(status_code=410, detail="This QR code is inactive")

    # Prefer the durable first-party HttpOnly cookie when it already exists.
    # The browser payload remains the bootstrap/fallback when cookies are absent
    # or have been cleared. This improves repeat-device continuity without
    # covert fingerprinting.
    cookie_visitor = (request.cookies.get("tti_qr_visitor") or "").strip()[:160]
    visitor_token = cookie_visitor or payload.visitor_id.strip()[:160]
    event_token = payload.event_id.strip()[:160]
    scanner_email = ""
    if code.identity_mode == "email":
        scanner_email = _clean_email(payload.scanner_email)
    elif payload.scanner_email:
        try:
            scanner_email = _clean_email(payload.scanner_email)
        except HTTPException:
            scanner_email = ""
    visitor_hash = stable_hash("qr-visitor-v2", visitor_token)
    event_hash = stable_hash("qr-event-v2", code.id, event_token)
    country, device, browser, operating_system = _qr_client_profile(request)
    platform, confidence, referrer_host = _qr_source_platform(
        payload.source_tag,
        payload.referrer,
        request.headers.get("user-agent") or "",
    )

    telemetry_data = payload.telemetry.model_dump(exclude_none=True)
    telemetry_data["form_factors"] = [str(value)[:30] for value in telemetry_data.get("form_factors", [])[:8] if str(value).strip()]
    telemetry_data["languages"] = [str(value)[:30] for value in telemetry_data.get("languages", [])[:12] if str(value).strip()]
    telemetry_json = json.dumps(telemetry_data, ensure_ascii=False, separators=(",", ":"))

    row_id = database.record_qr_scan(
        qr_id=code.id,
        scanned_at=datetime.now(UTC),
        visitor_hash=visitor_hash,
        event_hash=event_hash,
        confirmed=True,
        country=country,
        device_type=device,
        browser=browser,
        operating_system=operating_system,
        platform=platform,
        source_confidence=confidence,
        referrer_host=referrer_host,
        language=(payload.language or "")[:40],
        timezone=(payload.timezone or "")[:80],
        scanner_email=scanner_email,
        device_model=(payload.device_model or "")[:120],
        client_platform=(payload.client_platform or "")[:120],
        telemetry_json=telemetry_json,
        screen_width=payload.screen_width,
        screen_height=payload.screen_height,
    )
    response = JSONResponse(
        content={
            "recorded": row_id is not None,
            "platform": platform,
            "source_confidence": confidence,
            "identified": bool(scanner_email),
        },
        headers={"Cache-Control": "no-store"},
    )
    _set_qr_visitor_cookie(response, request, visitor_token, True)
    return response


@router.get("/qr/scan/{slug}", include_in_schema=False)
def scan_qr_code(
    slug: str,
    request: Request,
    database: Database = Depends(get_database),
) -> RedirectResponse:
    """Compatibility redirect for older direct-backend links.

    These requests are preserved as legacy/unverified data and are excluded from
    the v1.0.20 verified human scan KPIs.
    """
    code = database.get_qr_code_by_slug(slug)
    if code is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if not code.active:
        raise HTTPException(status_code=410, detail="This QR code is inactive")
    visitor_token, is_new_visitor = _record_legacy_qr_scan(code, request, database)
    action_kind, action_url, _ = _qr_action(code)
    if action_kind == "redirect" and action_url:
        response = RedirectResponse(url=action_url, status_code=302)
    elif code.qr_type in {"calendar", "contact"}:
        response = RedirectResponse(url=f"/api/v1/qr/action/{code.slug}", status_code=302)
    else:
        response = RedirectResponse(url=_qr_tracking_url(code), status_code=302)
    _set_qr_visitor_cookie(response, request, visitor_token, is_new_visitor)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/qr-analytics", response_model=QrAnalyticsSummary)
def qr_analytics(
    qr_id: str | None = Query(None),
    database: Database = Depends(get_database),
) -> QrAnalyticsSummary:
    if qr_id and database.get_qr_code(qr_id) is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    return database.qr_analytics(qr_id=qr_id)


@router.get("/qr-scans/export.csv")
def export_qr_scans(
    qr_id: str | None = Query(None),
    database: Database = Depends(get_database),
) -> Response:
    rows = database.qr_scan_rows(qr_id=qr_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "QR Name", "Scanned At UTC", "Data Quality", "Country", "Device", "Operating System",
        "Browser", "Browser Version", "Device Model", "Anonymous Device ID", "Scanner Email", "Source Platform", "Attribution", "Referrer Host", "Language", "Timezone", "Client Platform", "Platform Version", "Architecture", "Bitness", "Approx RAM GB", "Logical CPU Cores", "Touch Points", "Pixel Ratio", "Screen Width", "Screen Height", "Viewport Width", "Viewport Height", "Color Depth", "Connection Type", "Effective Connection", "Downlink Mbps", "RTT ms", "Save Data", "Form Factors", "Browser Vendor", "Screen Orientation", "Cookies Enabled", "Standalone/PWA", "Primary Pointer", "Hover Capable", "Color Gamut", "Browser Languages", "Timezone Offset Minutes"
    ])
    for row in rows:
        try:
            telemetry = json.loads(str(row["telemetry_json"] or "{}"))
            if not isinstance(telemetry, dict):
                telemetry = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            telemetry = {}
        writer.writerow([
            row["qr_name"],
            row["scanned_at"],
            "Verified" if int(row["confirmed"] or 0) == 1 else "Legacy",
            row["country"],
            row["device_type"],
            row["operating_system"],
            row["browser"],
            telemetry.get("browser_version") or "",
            row["device_model"],
            f"Device {str(row['visitor_hash'])[:8].upper()}",
            row["scanner_email"],
            row["platform"],
            row["source_confidence"],
            row["referrer_host"],
            row["language"],
            row["timezone"],
            row["client_platform"],
            telemetry.get("platform_version") or "",
            telemetry.get("architecture") or "",
            telemetry.get("bitness") or "",
            telemetry.get("device_memory_gb") if telemetry.get("device_memory_gb") is not None else "",
            telemetry.get("hardware_concurrency") if telemetry.get("hardware_concurrency") is not None else "",
            telemetry.get("max_touch_points") if telemetry.get("max_touch_points") is not None else "",
            telemetry.get("pixel_ratio") if telemetry.get("pixel_ratio") is not None else "",
            row["screen_width"],
            row["screen_height"],
            telemetry.get("viewport_width") if telemetry.get("viewport_width") is not None else "",
            telemetry.get("viewport_height") if telemetry.get("viewport_height") is not None else "",
            telemetry.get("color_depth") if telemetry.get("color_depth") is not None else "",
            telemetry.get("connection_type") or "",
            telemetry.get("effective_connection_type") or "",
            telemetry.get("downlink_mbps") if telemetry.get("downlink_mbps") is not None else "",
            telemetry.get("rtt_ms") if telemetry.get("rtt_ms") is not None else "",
            telemetry.get("save_data") if telemetry.get("save_data") is not None else "",
            ", ".join(str(v) for v in (telemetry.get("form_factors") or [])[:8]) if isinstance(telemetry.get("form_factors"), list) else "",
            telemetry.get("browser_vendor") or "",
            telemetry.get("screen_orientation") or "",
            telemetry.get("cookies_enabled") if telemetry.get("cookies_enabled") is not None else "",
            telemetry.get("standalone") if telemetry.get("standalone") is not None else "",
            telemetry.get("primary_pointer") or "",
            telemetry.get("hover_capable") if telemetry.get("hover_capable") is not None else "",
            telemetry.get("color_gamut") or "",
            ", ".join(str(v) for v in (telemetry.get("languages") or [])[:12]) if isinstance(telemetry.get("languages"), list) else "",
            telemetry.get("timezone_offset_minutes") if telemetry.get("timezone_offset_minutes") is not None else "",
        ])
    filename = "qr-scan-analytics.csv" if not qr_id else f"qr-scan-{qr_id[:8]}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(database: Database = Depends(get_database)) -> DashboardSummary:
    counts = database.dashboard_counts()
    last_sync = counts["last_successful_sync"]
    return DashboardSummary(
        connected_sources=int(counts["connected_sources"] or 0),
        tabs_scanned=int(counts["tabs_scanned"] or 0),
        timetable_entries=int(counts["timetable_entries"] or 0),
        content_items=int(counts["content_items"] or 0),
        videos=int(counts["videos"] or 0),
        pdfs=int(counts["pdfs"] or 0),
        changes_today=int(counts["changes_today"] or 0),
        sync_errors=int(counts["sync_errors"] or 0),
        last_successful_sync=datetime.fromisoformat(str(last_sync)) if last_sync else None,
    )


@router.get("/sources", response_model=list[SheetSource])
def list_sources(database: Database = Depends(get_database)) -> list[SheetSource]:
    return database.list_sources()


@router.get("/source-analysis", response_model=list[SourceAnalysisSummary])
def source_analysis(database: Database = Depends(get_database)) -> list[SourceAnalysisSummary]:
    results: list[SourceAnalysisSummary] = []
    for source in database.list_sources():
        timetable_count, content_count = database.source_record_counts(source.id)
        profile = database.get_workbook_profile(source.id)
        tabs = profile.tabs if profile else []
        results.append(
            SourceAnalysisSummary(
                source=source,
                profile=profile,
                timetable_count=timetable_count,
                content_count=content_count,
                test_count=database.source_test_count(source.id),
                search_ready_tabs=sum(1 for tab in tabs if tab.search_ready and tab.non_empty_cells > 0),
                needs_setup_tabs=sum(1 for tab in tabs if not tab.search_ready and tab.non_empty_cells > 0),
                tab_content_counts=database.content_counts_by_tab(source.id),
            )
        )
    return results


@router.get("/sources/{source_id}/profile", response_model=WorkbookProfile)
def source_profile(
    source_id: str,
    database: Database = Depends(get_database),
) -> WorkbookProfile:
    if database.get_source(source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")
    profile = database.get_workbook_profile(source_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Source has not completed an analysis yet")
    return profile


@router.get("/sources/{source_id}", response_model=SheetSource)
def get_source(
    source_id: str,
    database: Database = Depends(get_database),
) -> SheetSource:
    source = database.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources", response_model=SheetSource, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    database: Database = Depends(get_database),
) -> SheetSource:
    try:
        spreadsheet_id = extract_spreadsheet_id(str(payload.url))
    except InvalidGoogleSheetUrl as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    source_id = stable_hash("source", spreadsheet_id)
    existing = database.get_source(source_id)
    source = SheetSource(
        id=source_id,
        name=payload.name,
        url=str(payload.url),
        spreadsheet_id=spreadsheet_id,
        enabled=payload.enabled,
        created_at=existing.created_at if existing else datetime.now(UTC),
        last_sync_at=existing.last_sync_at if existing else None,
        last_sync_status=existing.last_sync_status if existing else "never",
        last_error=existing.last_error if existing else None,
    )
    database.upsert_source(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str,
    database: Database = Depends(get_database),
) -> Response:
    if database.get_source(source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")
    database.delete_source(source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sources/{source_id}/sync/start",
    response_model=SyncStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_source_sync(
    source_id: str,
    background_tasks: BackgroundTasks,
    database: Database = Depends(get_database),
    service: SyncService = Depends(get_sync_service),
) -> SyncStartResponse:
    source = database.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.enabled:
        raise HTTPException(status_code=409, detail="Source is disabled")
    if source.last_sync_status in {"queued", "downloading", "analyzing"}:
        return SyncStartResponse(
            source_id=source.id,
            status=source.last_sync_status,
            message="This source is already being synchronized.",
        )
    database.update_source_sync_status(source.id, "queued")
    background_tasks.add_task(service.sync_source, source)
    return SyncStartResponse(
        source_id=source.id,
        status="queued",
        message="Synchronization started in the background.",
    )


@router.post("/sources/{source_id}/sync", response_model=SyncResult)
async def sync_source(
    source_id: str,
    database: Database = Depends(get_database),
    service: SyncService = Depends(get_sync_service),
) -> SyncResult:
    source = database.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.enabled:
        raise HTTPException(status_code=409, detail="Source is disabled")
    return await service.sync_source(source)


@router.post("/sync-all/start")
def start_all_source_sync(
    background_tasks: BackgroundTasks,
    database: Database = Depends(get_database),
    service: SyncService = Depends(get_sync_service),
) -> dict[str, object]:
    queued: list[str] = []
    skipped: list[str] = []
    for source in database.list_sources():
        current = database.get_source(source.id)
        if current is None or not current.enabled:
            skipped.append(source.id)
            continue
        if current.last_sync_status in {"queued", "downloading", "analyzing"}:
            skipped.append(source.id)
            continue
        database.update_source_sync_status(current.id, "queued")
        background_tasks.add_task(service.sync_source, current)
        queued.append(current.id)
    return {
        "status": "queued" if queued else "nothing_to_queue",
        "queued_source_ids": queued,
        "skipped_source_ids": skipped,
        "message": (
            f"Checking {len(queued)} Google Sheet connection(s) in the background."
            if queued
            else "All enabled Google Sheets are already being checked."
        ),
    }


@router.get("/timetable", response_model=PaginatedResponse)
def timetable(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    class_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    stream: str | None = None,
    class_name: str | None = None,
    subject: str | None = None,
    latest: bool = Query(False, description="Show the final available timetable date when no date is supplied"),
    upcoming: bool = Query(False, description="Show the nearest available date from today onward"),
    database: Database = Depends(get_database),
) -> PaginatedResponse:
    items, total = database.list_timetable_page(
        page=page,
        page_size=page_size,
        class_date=class_date,
        date_from=date_from,
        date_to=date_to,
        stream=stream,
        class_name=class_name,
        subject=subject,
        latest=latest,
        upcoming=upcoming,
    )
    pages = max(1, math.ceil(total / page_size))
    # Preserve the long-standing pagination contract used by clients and tests:
    # when data exists, requesting a page beyond the last available page is 404.
    # An actually empty result set still exposes page 1 with zero items.
    if total and page > pages:
        raise HTTPException(status_code=404, detail="Page is outside the available result set")
    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
    )


@router.get("/content", response_model=ContentSearchResponse)
def content(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = None,
    content_type: str | None = None,
    stream: str | None = None,
    subject: str | None = None,
    class_name: str | None = None,
    source_id: str | None = None,
    sheet_name: str | None = None,
    database: Database = Depends(get_database),
) -> PaginatedResponse:
    started = perf_time.perf_counter()
    if not query:
        page_items, total = database.list_content_page(
            page=page,
            page_size=page_size,
            source_id=source_id,
            sheet_name=sheet_name,
            content_type=content_type,
            stream=stream,
            subject=subject,
            class_name=class_name,
        )
        return ContentSearchResponse(
            items=page_items,
            page=page,
            page_size=page_size,
            total=total,
            pages=max(1, math.ceil(total / page_size)),
            search_ms=max(1, round((perf_time.perf_counter() - started) * 1000)),
            normalized_query=None,
        )

    items = database.search_content_candidates(query, SEARCH_ALIAS_GROUPS, source_id=source_id)
    if query:
        ranked = [
            (score, item)
            for item in items
            if (score := _content_search_score(item, query)) > 0
        ]
        ranked.sort(
            key=lambda pair: (
                -pair[0],
                (getattr(pair[1], "subject", None) or "").casefold(),
                (getattr(pair[1], "title", None) or "").casefold(),
            )
        )
        items = [item for _, item in ranked]
    if content_type:
        items = [item for item in items if item.content_type.value == content_type]
    if stream:
        items = [item for item in items if _contains(item.stream, stream)]
    if subject:
        items = [item for item in items if _contains(item.subject, subject)]
    if class_name:
        items = [item for item in items if _contains(item.class_name, class_name)]
    if sheet_name:
        items = [item for item in items if item.sheet_name.casefold() == sheet_name.casefold()]
    response = _paginate(items, page, page_size)
    return ContentSearchResponse(
        items=response.items,
        page=response.page,
        page_size=response.page_size,
        total=response.total,
        pages=response.pages,
        search_ms=max(1, round((perf_time.perf_counter() - started) * 1000)),
        normalized_query=_search_normalize(query) if query else None,
    )


@router.get("/changes/summary", response_model=ChangeSummary)
def changes_summary(
    source_id: str | None = None,
    sheet_name: str | None = None,
    period: Literal["today", "yesterday", "7days", "all"] = "today",
    database: Database = Depends(get_database),
) -> ChangeSummary:
    items = _filter_changes(database.list_changes(limit=10000), period, source_id, None, sheet_name)
    stories = _group_change_stories(items)
    return ChangeSummary(
        added=sum(item.change_type.value == "added" for item in stories),
        updated=sum(item.change_type.value == "updated" for item in stories),
        deleted=sum(item.change_type.value == "deleted" for item in stories),
        total=len(stories),
        sources_checked=len({item.source_id for item in stories}),
    )


@router.get("/changes", response_model=PaginatedResponse)
def changes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: str | None = None,
    sheet_name: str | None = None,
    change_type: str | None = None,
    period: Literal["today", "yesterday", "7days", "all"] = "today",
    view: Literal["cells", "stories"] = "stories",
    database: Database = Depends(get_database),
) -> PaginatedResponse:
    items = _filter_changes(database.list_changes(limit=5000), period, source_id, change_type, sheet_name)
    if view == "stories":
        friendly_items = [_friendly_change(item) for item in _group_change_stories(items)]
    else:
        friendly_items = [
            _friendly_change(item.model_copy(update={
                "details": [ChangeField(
                    field_name=item.field_name or item.coordinate,
                    change_type=item.change_type,
                    old_value=item.old_value,
                    new_value=item.new_value,
                    coordinate=item.coordinate,
                    row_number=_coordinate_row(item.coordinate) or None,
                )],
                "affected_rows": [_coordinate_row(item.coordinate)] if _coordinate_row(item.coordinate) else [],
                "affected_count": 1,
                "group_kind": "cell",
            }))
            for item in items
        ]
    return _paginate(friendly_items, page, page_size)


@router.get("/exports/changes/csv")
def export_changes_csv(
    period: Literal["today", "yesterday", "7days", "all"] = "today",
    source_id: str | None = None,
    sheet_name: str | None = None,
    change_type: str | None = None,
    database: Database = Depends(get_database),
) -> Response:
    items = _filter_changes(database.list_changes(limit=5000), period, source_id, change_type, sheet_name)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Detected at", "Workbook", "Tab", "Cell", "Change", "Before", "After"])
    for item in items:
        writer.writerow([
            item.detected_at.astimezone(INDIA_TIMEZONE).isoformat(),
            item.workbook_name, item.sheet_name, item.coordinate, item.change_type.value,
            item.old_value or "", item.new_value or "",
        ])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sheet-changes-{period}.csv"'},
    )


def _default_test_source(database: Database) -> SheetSource | None:
    for source in database.list_sources():
        if source.spreadsheet_id == "1ZYbITcTnAAbrLOyQ3pzaykEAmOt9Q1EH6gkImY33JXQ":
            return source
    return None


def _test_status_bucket(records: list[TestRecord], field: str, label: str) -> TestStatusBucket:
    if field in {"result_dashboard", "video_solution_update"}:
        due = [item for item in records if test_is_due(item, datetime.now(INDIA_TIMEZONE).date())]
        not_due = len(records) - len(due)
    else:
        due = records
        not_due = 0
    done = sum(status_is_done(getattr(item, field)) for item in due)
    return TestStatusBucket(
        label=label,
        total=len(due),
        done=done,
        pending=len(due) - done,
        not_due=not_due,
    )


@router.get("/test-monitor/tabs", response_model=dict[str, int])
def test_monitor_tabs(
    background_tasks: BackgroundTasks,
    source_id: str | None = None,
    database: Database = Depends(get_database),
) -> dict[str, int]:
    """Lightweight Test Monitor navigation counts.

    The tab bar must never require the full Test Monitor analytics payload.
    """
    if source_id is None:
        default_source = _default_test_source(database)
        source_id = default_source.id if default_source else None
    counts = database.test_sheet_counts(source_id=source_id)
    if source_id and counts:
        now = perf_time.monotonic()
        with _TEST_MONITOR_CACHE_LOCK:
            warm_until = _TEST_MONITOR_WARM_UNTIL.get(source_id, 0.0)
            should_warm = now >= warm_until
            if should_warm:
                _TEST_MONITOR_WARM_UNTIL[source_id] = now + 60.0
        if should_warm:
            background_tasks.add_task(_warm_test_monitor_tabs, database, source_id, list(counts))
    return counts


@router.get("/test-monitor", response_model=TestMonitorResponse)
def test_monitor(
    source_id: str | None = None,
    sheet_name: str | None = None,
    compact: bool = True,
    database: Database = Depends(get_database),
) -> TestMonitorResponse:
    if source_id is None:
        default_source = _default_test_source(database)
        source_id = default_source.id if default_source else None
    cache_key = (source_id or "", sheet_name or "", compact)
    cached = _test_monitor_cache_get(cache_key)
    if cached is not None:
        return cached
    records = database.list_test_records(
        source_id=source_id,
        sheet_names=[sheet_name] if sheet_name else None,
    )
    now = datetime.now(UTC)
    india_now = datetime.now(INDIA_TIMEZONE)
    window_start, window_end, sunday_date, result_deadline, video_deadline = weekly_cycle(india_now)
    upcoming_sunday_tests = tests_for_sunday(records, sunday_date)
    recent_cutoff = now - timedelta(days=7)
    recent_matches = [item for item in records if item.first_seen_at and item.first_seen_at >= recent_cutoff]
    recent_count = len(recent_matches)
    recent = [] if compact else sorted(
        recent_matches,
        key=lambda item: item.first_seen_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    # The operational reports requested by the admin have different scopes:
    # - App Status: PRARAMBH 2026 + Nirman 2026
    # - Result Dashboard and Video Solution: PRARAMBH 2026 only
    # When a specific tab is selected, all three cards use that selected tab.
    if sheet_name:
        app_records = records
        result_records = records
    else:
        app_tabs = {"prarambh 2026", "nirman 2026"}
        app_records = [item for item in records if item.sheet_name.casefold() in app_tabs]
        result_records = [item for item in records if item.sheet_name.casefold() == "prarambh 2026"]

    pending_app = [item for item in app_records if not status_is_done(item.app_status)]
    due_result = [
        item for item in result_records
        if test_is_due(item, datetime.now(INDIA_TIMEZONE).date())
    ]
    pending_result = [item for item in due_result if not status_is_done(item.result_dashboard)]
    pending_video = [item for item in due_result if not status_is_done(item.video_solution_update)]
    sheet_counts: dict[str, int] = {}
    subject_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    course_counts: dict[str, int] = {}
    for item in records:
        sheet_counts[item.sheet_name] = sheet_counts.get(item.sheet_name, 0) + 1
        if item.subject:
            subject_counts[item.subject] = subject_counts.get(item.subject, 0) + 1
        if item.class_name:
            class_counts[item.class_name] = class_counts.get(item.class_name, 0) + 1
        if item.course:
            course_counts[item.course] = course_counts.get(item.course, 0) + 1
    tests_with_clickable_files = sum(bool(item.document_url or item.pdf_url) for item in records)
    scheduled_tests = sum(bool(item.test_date_status) for item in records)
    data_quality = TestDataQuality(
        total=len(records),
        missing_course=sum(not item.course for item in records),
        missing_class=sum(not item.class_name for item in records),
        missing_subject=sum(not item.subject for item in records),
        missing_topic=sum(not (item.topic or item.chapter_number) for item in records),
        missing_file_name=sum(not (item.document_title or item.pdf_title) for item in records),
        missing_clickable_link=sum(
            bool(item.document_title or item.pdf_title) and not (item.document_url or item.pdf_url)
            for item in records
        ),
        missing_app_status=sum(not item.app_status for item in app_records),
        missing_test_date=sum(not item.test_date_status for item in result_records),
        missing_result_dashboard=sum(not item.result_dashboard for item in result_records),
        missing_video_solution=sum(not item.video_solution_update for item in result_records),
    )
    cycle_subject_counts: dict[str, int] = {}
    cycle_class_counts: dict[str, int] = {}
    cycle_course_counts: dict[str, int] = {}
    for item in upcoming_sunday_tests:
        if item.subject:
            cycle_subject_counts[item.subject] = cycle_subject_counts.get(item.subject, 0) + 1
        if item.class_name:
            cycle_class_counts[item.class_name] = cycle_class_counts.get(item.class_name, 0) + 1
        if item.course:
            cycle_course_counts[item.course] = cycle_course_counts.get(item.course, 0) + 1
    cycle_done = sum(status_is_done(item.app_status) for item in upcoming_sunday_tests)

    response = TestMonitorResponse(
        summary=TestMonitorSummary(
            total_tests=len(records),
            new_tests_7days=recent_count,
            app_status=_test_status_bucket(app_records, "app_status", "App Status"),
            result_dashboard=_test_status_bucket(result_records, "result_dashboard", "Result Dashboard"),
            video_solution=_test_status_bucket(result_records, "video_solution_update", "Video Solution"),
            sheet_counts=sheet_counts,
            subject_counts=dict(sorted(subject_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
            class_counts=dict(sorted(class_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
            course_counts=dict(sorted(course_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
            tests_with_clickable_files=tests_with_clickable_files,
            tests_without_clickable_files=len(records) - tests_with_clickable_files,
            scheduled_tests=scheduled_tests,
            data_quality=data_quality,
            generated_at=datetime.now(UTC),
        ),
        cycle=TestCycleSummary(
            window_start=window_start,
            window_end=window_end,
            sunday_date=sunday_date,
            result_deadline=result_deadline,
            video_deadline=video_deadline,
            window_open=window_start <= india_now <= window_end,
            total_tests=len(upcoming_sunday_tests),
            app_done=cycle_done,
            app_pending=len(upcoming_sunday_tests) - cycle_done,
            subject_counts=dict(sorted(cycle_subject_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
            class_counts=dict(sorted(cycle_class_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
            course_counts=dict(sorted(cycle_course_counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))),
        ),
        upcoming_sunday_tests=upcoming_sunday_tests[:120] if compact else upcoming_sunday_tests[:300],
        pending_app=pending_app[:20] if compact else pending_app[:200],
        pending_result=pending_result[:20] if compact else pending_result[:200],
        pending_video=pending_video[:20] if compact else pending_video[:200],
        recent_tests=[] if compact else recent[:100],
    )
    return _test_monitor_cache_put(cache_key, response)


@router.post("/notification-presets/test-monitor", response_model=list[NotificationRule])
def create_test_notification_presets(
    payload: TestNotificationPresetRequest,
    database: Database = Depends(get_database),
) -> list[NotificationRule]:
    source = database.get_source(payload.source_id) if payload.source_id else _default_test_source(database)
    if source is None:
        raise HTTPException(status_code=404, detail="Test Series - 2026 is not connected")
    created = datetime.now(UTC)
    specs = [
        ("new_test_added", "New test added", None, None, ["PRARAMBH 2026", "Nirman 2026"]),
        ("test_app_status", "Saturday 6 PM Sunday Test Readiness", payload.app_status_time, 5, ["PRARAMBH 2026", "Nirman 2026"]),
        ("test_result_dashboard", "Monday 6 PM Result Dashboard", payload.result_time, 0, ["PRARAMBH 2026"]),
        ("test_video_solution", "Tuesday 6 PM Video Solution", payload.video_time, 1, ["PRARAMBH 2026"]),
    ]
    rules: list[NotificationRule] = []
    for event_type, name, send_time, weekday, sheet_names in specs:
        rule = NotificationRule(
            id=stable_hash("test-preset", source.id, event_type, payload.channel, payload.recipient),
            name=name,
            enabled=True,
            event_type=event_type,
            send_time=send_time,
            weekday=weekday,
            channels=[payload.channel],
            recipients=[payload.recipient],
            source_ids=[source.id],
            sheet_names=sheet_names,
            created_at=created,
        )
        database.upsert_notification_rule(rule)
        rules.append(rule)
    return rules


@router.get("/notification-rules", response_model=list[NotificationRule])
def notification_rules(database: Database = Depends(get_database)) -> list[NotificationRule]:
    return database.list_notification_rules()


@router.post(
    "/notification-rules",
    response_model=NotificationRule,
    status_code=status.HTTP_201_CREATED,
)
def create_notification_rule(
    payload: NotificationRule,
    database: Database = Depends(get_database),
) -> NotificationRule:
    database.upsert_notification_rule(payload)
    return payload


@router.get("/notification-status", response_model=NotificationStatus)
def notification_status(database: Database = Depends(get_database)) -> NotificationStatus:
    configured = NotificationService(database).configured_channels()
    return NotificationStatus(
        scheduler_active=True,
        scheduler_interval_seconds=settings.notification_interval_seconds,
        sheet_refresh_minutes=settings.sync_interval_minutes,
        page_refresh_minutes=settings.page_refresh_minutes,
        configured_channels=configured,
    )


@router.get("/notification-deliveries", response_model=list[NotificationDelivery])
def notification_deliveries(
    limit: int = Query(30, ge=1, le=200),
    database: Database = Depends(get_database),
) -> list[NotificationDelivery]:
    return database.list_notification_deliveries(limit=limit)


@router.delete("/notification-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification_rule(
    rule_id: str,
    database: Database = Depends(get_database),
) -> Response:
    if database.get_notification_rule(rule_id) is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    database.delete_notification_rule(rule_id, delete_history=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/notification-rules/{rule_id}/test", response_model=NotificationTestResponse)
async def test_notification_rule(
    rule_id: str,
    database: Database = Depends(get_database),
) -> NotificationTestResponse:
    rule = database.get_notification_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    preview, deliveries = await NotificationService(database).test_rule(rule)
    return NotificationTestResponse(
        rule_id=rule.id,
        scheduler_ok=True,
        preview=preview,
        deliveries=deliveries,
    )


@router.get("/exports/timetable/{file_type}")
def export_timetable(
    file_type: Literal["xlsx", "pdf"],
    class_date: date | None = None,
    database: Database = Depends(get_database),
) -> Response:
    entries = database.list_timetable()
    if class_date:
        entries = [entry for entry in entries if entry.class_date == class_date]
    if file_type == "xlsx":
        content = build_timetable_xlsx(entries)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        title = f"Timetable - {class_date.isoformat()}" if class_date else "Timetable"
        content = build_timetable_pdf(entries, title)
        media_type = "application/pdf"
    filename = f"timetable-{class_date or 'all'}.{file_type}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



def _filter_changes(
    items: list[ChangeRecord],
    period: str,
    source_id: str | None,
    change_type: str | None,
    sheet_name: str | None = None,
) -> list[ChangeRecord]:
    local_today = datetime.now(INDIA_TIMEZONE).date()
    if period == "today":
        items = [item for item in items if item.detected_at.astimezone(INDIA_TIMEZONE).date() == local_today]
    elif period == "yesterday":
        target = local_today - timedelta(days=1)
        items = [item for item in items if item.detected_at.astimezone(INDIA_TIMEZONE).date() == target]
    elif period == "7days":
        start = local_today - timedelta(days=6)
        items = [item for item in items if start <= item.detected_at.astimezone(INDIA_TIMEZONE).date() <= local_today]
    if source_id:
        items = [item for item in items if item.source_id == source_id]
    if change_type:
        items = [item for item in items if item.change_type.value == change_type]
    if sheet_name:
        items = [item for item in items if item.sheet_name.casefold() == sheet_name.casefold()]
    return items



def _coordinate_row(coordinate: str) -> int:
    match = re.search(r"(\d+)$", coordinate or "")
    return int(match.group(1)) if match else 0


def _group_change_stories(items: list[ChangeRecord]) -> list[ChangeRecord]:
    """Convert technical cell edits into deduplicated human-readable change events.

    Priority is deliberate:
    1. Multiple cells in the same source row/check become one row story.
    2. Only single-field row stories are then eligible for bulk grouping when the
       same field changes across multiple rows in the same check.
    3. Every raw cell belongs to exactly one resulting story.
    """
    row_groups: dict[tuple[str, str, str, int, str], list[ChangeRecord]] = {}
    for item in items:
        local_stamp = item.detected_at.astimezone(INDIA_TIMEZONE).replace(second=0, microsecond=0).isoformat()
        key = (
            item.source_id,
            item.workbook_name,
            item.sheet_name,
            _coordinate_row(item.coordinate),
            local_stamp,
        )
        row_groups.setdefault(key, []).append(item)

    row_stories: list[ChangeRecord] = []
    for (source_id, workbook, sheet, row_number, stamp), changes in row_groups.items():
        types = {item.change_type.value for item in changes}
        if len(types) == 1:
            story_type = changes[0].change_type
        elif "updated" in types:
            story_type = "updated"
        elif "added" in types:
            story_type = "added"
        else:
            story_type = "deleted"
        before_values = list(dict.fromkeys(item.old_value for item in changes if item.old_value))
        after_values = list(dict.fromkeys(item.new_value for item in changes if item.new_value))
        before = " | ".join(before_values[:5]) or None
        after = " | ".join(after_values[:5]) or None
        row_label = next((item.row_label for item in changes if item.row_label and item.row_label != "Column headings"), None)
        details = [
            ChangeField(
                field_name=item.field_name or item.coordinate,
                change_type=item.change_type,
                old_value=item.old_value,
                new_value=item.new_value,
                coordinate=item.coordinate,
                row_number=row_number or None,
            )
            for item in sorted(changes, key=lambda value: value.coordinate)
        ]
        row_stories.append(
            ChangeRecord(
                id=stable_hash("change-story", source_id, sheet, row_number, stamp),
                source_id=source_id,
                workbook_name=workbook,
                sheet_name=sheet,
                coordinate=f"Row {row_number}" if row_number else "Sheet",
                change_type=story_type,
                old_value=before,
                new_value=after,
                detected_at=max(item.detected_at for item in changes),
                row_label=row_label,
                details=details,
                affected_rows=[row_number] if row_number else [],
                affected_count=1,
                group_kind="row",
            )
        )

    # Same field across different rows becomes one bulk story, but only after the
    # row grouping above. Multi-field row events are intentionally never split.
    bulk_groups: dict[tuple[str, str, str, str, str, str], list[ChangeRecord]] = {}
    for story in row_stories:
        if len(story.details) != 1 or not story.affected_rows:
            continue
        detail = story.details[0]
        if story.row_label == "Column headings":
            continue
        stamp = story.detected_at.astimezone(INDIA_TIMEZONE).replace(second=0, microsecond=0).isoformat()
        key = (
            story.source_id,
            story.workbook_name,
            story.sheet_name,
            _friendly_field_name(detail.field_name).casefold(),
            detail.change_type.value,
            stamp,
        )
        bulk_groups.setdefault(key, []).append(story)

    consumed: set[str] = set()
    stories: list[ChangeRecord] = []
    for key, candidates in bulk_groups.items():
        unique_rows = sorted({row for story in candidates for row in story.affected_rows})
        if len(unique_rows) < 2:
            continue
        source_id, workbook, sheet, _, _, stamp = key
        details = [detail for story in candidates for detail in story.details]
        field_name = details[0].field_name
        change_type = details[0].change_type
        before_values = list(dict.fromkeys(detail.old_value for detail in details if detail.old_value))
        after_values = list(dict.fromkeys(detail.new_value for detail in details if detail.new_value))
        stories.append(
            ChangeRecord(
                id=stable_hash("change-bulk-field", source_id, sheet, field_name, change_type.value, stamp),
                source_id=source_id,
                workbook_name=workbook,
                sheet_name=sheet,
                coordinate=f"{len(unique_rows)} rows",
                change_type=change_type,
                old_value=" | ".join(before_values[:5]) or None,
                new_value=" | ".join(after_values[:5]) or None,
                detected_at=max(story.detected_at for story in candidates),
                field_name=field_name,
                row_label=None,
                details=sorted(details, key=lambda value: (value.row_number or 0, value.coordinate or "")),
                affected_rows=unique_rows,
                affected_count=len(unique_rows),
                group_kind="field",
            )
        )
        consumed.update(story.id for story in candidates)

    stories.extend(story for story in row_stories if story.id not in consumed)
    return sorted(stories, key=lambda item: item.detected_at, reverse=True)


def _search_normalize(value: str | None) -> str:
    return normalize_search_text(value or "")


SEARCH_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("math", "maths", "mathematics", "गणित", "ganit"),
    ("science", "विज्ञान", "vigyan"),
    ("physics", "भौतिक", "भौतिकी", "bhautik"),
    ("chemistry", "रसायन", "रसायनविज्ञान", "rasayan"),
    ("biology", "जीवविज्ञान", "जीव विज्ञान", "jeev vigyan"),
    ("english", "अंग्रेजी", "अँग्रेज़ी", "angrezi"),
    ("hindi", "हिंदी", "हिन्दी", "hindī"),
    ("sanskrit", "संस्कृत", "संस्कृतम्", "sanskritam"),
    ("social science", "sst", "सामाजिक विज्ञान", "samajik vigyan"),
    ("history", "इतिहास", "itihas"),
    ("geography", "भूगोल", "bhugol"),
    ("political science", "civics", "राजनीति विज्ञान", "rajniti vigyan"),
    ("economics", "अर्थशास्त्र", "arthashastra"),
    ("accountancy", "accounts", "accounting", "लेखाशास्त्र", "lekhashastra"),
    ("business studies", "bst", "व्यवसाय अध्ययन", "vyavsay adhyayan"),
    ("light", "lights", "प्रकाश", "roshni"),
    ("electronics", "electronic", "इलेक्ट्रॉनिक्स"),
    ("base", "bases", "alkali", "क्षार", "आधार"),
    ("acid", "acids", "अम्ल"),
)


def _alias_choices(token: str) -> tuple[str, ...]:
    normalized = _search_normalize(token)
    for group in SEARCH_ALIAS_GROUPS:
        expanded: set[str] = set()
        for item in group:
            value = _search_normalize(item)
            expanded.add(value)
            expanded.update(value.split())
        if normalized in expanded or any(part in expanded for part in normalized.split()):
            return tuple(sorted(expanded))
    return tuple(normalized.split()) or (normalized,)


def _word_match_score(query_word: str, candidate_word: str) -> int:
    if not query_word or not candidate_word:
        return 0
    if query_word == candidate_word:
        return 26
    if candidate_word.startswith(query_word) or query_word.startswith(candidate_word):
        if min(len(query_word), len(candidate_word)) >= 3:
            return 20
    if query_word in candidate_word or candidate_word in query_word:
        if min(len(query_word), len(candidate_word)) >= 3:
            return 17
    if min(len(query_word), len(candidate_word)) >= 4:
        ratio = SequenceMatcher(None, query_word, candidate_word).ratio()
        if ratio >= 0.86:
            return 14
        if ratio >= 0.76:
            return 9
    return 0


def _content_search_score(item: object, query: str) -> int:
    fields = [
        getattr(item, "title", None), getattr(item, "url", None),
        getattr(item, "stream", None), getattr(item, "class_name", None),
        getattr(item, "batch", None), getattr(item, "subject", None),
        getattr(item, "topic", None), getattr(item, "teacher", None),
        getattr(item, "sheet_name", None), getattr(item, "workbook_name", None),
        getattr(item, "search_text", None),
        getattr(item, "status", None), getattr(item, "test_number", None),
        getattr(item, "test_date", None), getattr(item, "result_dashboard", None),
        getattr(item, "video_solution_update", None), getattr(item, "remarks", None),
        getattr(getattr(item, "content_type", None), "value", None),
    ]
    raw = " ".join(str(value) for value in fields if value)
    raw_folded = raw.casefold()
    query_folded = query.casefold().strip()
    if not query_folded:
        return 0
    score = 0
    if query_folded in raw_folded:
        score += 140

    blob = _search_normalize(raw)
    words = blob.split()
    normalized_query = _search_normalize(query)
    if normalized_query and normalized_query in blob:
        score += 110

    query_tokens = normalized_query.split()
    if not query_tokens:
        return score
    matched_tokens = 0
    for token in query_tokens:
        best = 0
        for alias in _alias_choices(token):
            alias_words = alias.split()
            if len(alias_words) > 1 and alias in blob:
                best = max(best, 34)
            for alias_word in alias_words:
                for candidate in words:
                    best = max(best, _word_match_score(alias_word, candidate))
        if best:
            matched_tokens += 1
            score += best

    if matched_tokens == 0:
        return 0
    score += matched_tokens * 8
    if matched_tokens == len(query_tokens):
        score += 24
    return score


def _content_matches(item: object, query: str) -> bool:
    return _content_search_score(item, query) > 0


def _friendly_field_name(value: str | None) -> str:
    text = (value or "Information").strip().replace("_", " ")
    if re.fullmatch(r"[A-Za-z]+\d+", text):
        return "Information"
    aliases = {
        "yt link": "YouTube link",
        "video solution upodat": "Video Solution",
        "video solution update": "Video Solution",
        "result deshbord": "Result Dashboard",
        "result dashboard": "Result Dashboard",
        "app status": "App Status",
        "test date": "Test Date",
        "docs link": "Test file",
        "pdf": "PDF file",
        "topic": "Topic",
        "chapter name": "Chapter / topic",
        "subject teacher": "Teacher",
        "remarks": "Link / remarks",
    }
    return aliases.get(text.casefold(), text[:1].upper() + text[1:])


def _best_change_detail(item: ChangeRecord) -> ChangeField | None:
    preferred = (
        "app status", "result dashboard", "result deshbord", "video solution",
        "topic", "chapter", "subject", "teacher", "yt link", "video", "pdf",
        "docs link", "file", "date", "time",
    )
    for needle in preferred:
        match = next((detail for detail in item.details if needle in detail.field_name.casefold() and detail.old_value != detail.new_value), None)
        if match:
            return match
    return next((detail for detail in item.details if detail.old_value != detail.new_value), item.details[0] if item.details else None)


def _friendly_change(item: ChangeRecord) -> ChangeRecord:
    before = item.old_value or ""
    after = item.new_value or ""
    combined = f"{before} {after}".casefold()
    tab = item.sheet_name.casefold()
    workbook = item.workbook_name.casefold()
    fields = {detail.field_name.casefold() for detail in item.details}
    has_learning_file = (
        "http://" in combined
        or "https://" in combined
        or any(extension in combined for extension in (
            ".pdf", ".mp4", ".mov", ".webm", ".doc", ".docx", ".ppt", ".pptx"
        ))
        or any(word in " ".join(fields) for word in ("pdf", "video", "docs link", "file link", "yt link"))
    )
    is_timetable = any(word in tab for word in ("time table", "timetable", "planner"))
    is_test_series = (
        "test" in workbook
        or "test" in tab
        or "cuet" in tab
        or "paper" in combined
        or ".docx" in combined
        or any(word in " ".join(fields) for word in ("app status", "result", "video solution", "test date"))
    )

    if is_timetable:
        category = "Timetable"
        noun = "class"
        impact = "Today, Weekly Timetable and timetable notifications will use this update."
    elif is_test_series:
        category = "Test series"
        noun = "test"
        impact = "Search, Test Analysis and test notifications will use this update."
    elif has_learning_file:
        category = "Learning file"
        noun = "learning file"
        impact = "This update changes what users can find in Learning Files."
    else:
        category = "Sheet information"
        noun = "information"
        impact = "This information is saved in the change history for review."

    descriptor = (item.row_label or "").strip()
    if not descriptor:
        value = after or before
        descriptor = value.split(" — http", 1)[0].strip()
        if " | " in descriptor:
            parts = [part.strip() for part in descriptor.split(" | ") if part.strip()]
            descriptor = " → ".join(parts[:4])
    if len(descriptor) > 150:
        descriptor = descriptor[:147].rstrip() + "…"

    detail = _best_change_detail(item)
    field_label = _friendly_field_name(detail.field_name if detail else item.field_name)
    detail_before = (detail.old_value if detail else item.old_value) or "Blank"
    detail_after = (detail.new_value if detail else item.new_value) or "Blank"

    detail_type = detail.change_type.value if detail else item.change_type.value
    if item.group_kind == "field" and item.affected_count > 1:
        if detail_type == "added":
            summary = f"{field_label} added in {item.affected_count} rows"
        elif detail_type == "deleted":
            summary = f"{field_label} removed from {item.affected_count} rows"
        else:
            summary = f"{field_label} changed in {item.affected_count} rows"
        descriptor = ""
    elif is_test_series and detail_type == "added" and field_label == "Information":
        summary = "New test file added"
    elif is_test_series and detail_type == "deleted" and field_label == "Information":
        summary = "Test file removed"
    elif item.change_type.value == "added":
        summary = f"New {noun} added"
        if detail and field_label not in {"Information", "Topic"}:
            summary = f"{field_label} added"
    elif item.change_type.value == "deleted":
        summary = f"{noun.title()} removed"
        if detail and field_label not in {"Information", "Topic"}:
            summary = f"{field_label} removed"
    else:
        summary = f"{field_label} changed from ‘{detail_before}’ to ‘{detail_after}’"
    if descriptor and item.change_type.value != "updated":
        summary = f"{summary}: {descriptor}"
    elif descriptor and item.change_type.value == "updated":
        summary = f"{summary} — {descriptor}"

    return item.model_copy(update={
        "category": category,
        "summary": summary,
        "impact": impact,
        # Raw row/cell coordinates are deliberately hidden from normal users.
        "plain_location": f"{item.workbook_name} → {item.sheet_name}",
    })


def _paginate(items: list[object], page: int, page_size: int) -> PaginatedResponse:
    total = len(items)
    pages = max(1, math.ceil(total / page_size))
    if page > pages and total:
        raise HTTPException(status_code=404, detail="Page is outside the available result set")
    start = (page - 1) * page_size
    return PaginatedResponse(
        items=items[start : start + page_size],
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
    )


def _contains(value: str | None, expected: str) -> bool:
    return expected.casefold() in (value or "").casefold()
