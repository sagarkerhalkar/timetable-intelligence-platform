"""QR Insights: one honest, read-only view of verified QR scans.

Nothing here writes to the database. Every number is computed from the raw
`qr_scans` rows that already exist, so improving a label (for example telling
Google Lens scans apart from Google Search clicks) also corrects old history.

Accuracy rules shown to people in the UI:
* Location comes from the visitor's network (Cloudflare IP geolocation). Country
  and state are reliable; the city is the network's city, which for Indian
  mobile data is often the operator's hub city rather than where the phone is.
* "Unique devices" are browser profiles, not people.
* One normal QR link is used everywhere. A source is "Detected" when the app's
  in-app browser names itself or the phone reports the opening app/site, "Tagged"
  for older links that carried ?src=..., and "Not reported" otherwise (most
  phone-camera scans).
"""
from __future__ import annotations

import copy
import csv
import io
import threading
import time
from array import array
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response

from ..dependencies import get_database

router = APIRouter(prefix="/api/v1/qr-insights", tags=["qr-insights"])

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365, "all": None}
_CACHE_TTL_SECONDS = 60.0
_CACHE: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()

# --------------------------------------------------------------------------
# Source classification
# --------------------------------------------------------------------------
# (channel id, label, group)
_TAGS: dict[str, tuple[str, str, str]] = {
    "whatsapp": ("whatsapp", "WhatsApp", "Messaging"),
    "telegram": ("telegram", "Telegram", "Messaging"),
    "instagram": ("instagram", "Instagram", "Social"),
    "facebook": ("facebook", "Facebook", "Social"),
    "messenger": ("facebook", "Facebook", "Social"),
    "youtube": ("youtube", "YouTube", "Social"),
    "linkedin": ("linkedin", "LinkedIn", "Social"),
    "x": ("x", "X / Twitter", "Social"),
    "twitter": ("x", "X / Twitter", "Social"),
    "x / twitter": ("x", "X / Twitter", "Social"),
    "email": ("email", "Email", "Messaging"),
    "sms": ("sms", "SMS", "Messaging"),
    "google-chat": ("google-chat", "Google Chat", "Messaging"),
    "google_chat": ("google-chat", "Google Chat", "Messaging"),
    "google chat": ("google-chat", "Google Chat", "Messaging"),
    "web": ("website", "Website", "Web"),
    "website": ("website", "Website", "Web"),
    "web / website": ("website", "Website", "Web"),
    "poster": ("print", "Printed QR", "Print"),
    "print": ("print", "Printed QR", "Print"),
    "book": ("print", "Printed QR", "Print"),
    "chatgpt.com": ("chatgpt", "ChatGPT", "AI assistants"),
    "chatgpt": ("chatgpt", "ChatGPT", "AI assistants"),
    "snapchat": ("snapchat", "Snapchat", "Social"),
    "pinterest": ("pinterest", "Pinterest", "Social"),
    "line": ("line", "Line", "Messaging"),
    "google app": ("google-lens", "Google Lens / Google app", "QR scanner apps"),
    "teams": ("teams", "Microsoft Teams", "Messaging"),
    "microsoft teams": ("teams", "Microsoft Teams", "Messaging"),
    "slack": ("slack", "Slack", "Messaging"),
    "discord": ("discord", "Discord", "Messaging"),
}

# Ordered: the first matching fragment of the referrer host wins.
_HOSTS: tuple[tuple[str, tuple[str, str, str]], ...] = (
    ("googlequicksearchbox", ("google-lens", "Google Lens / Google app", "QR scanner apps")),
    ("lens.google", ("google-lens", "Google Lens / Google app", "QR scanner apps")),
    ("apps.searchlite", ("google-go", "Google Go app", "QR scanner apps")),
    ("android.youtube", ("youtube", "YouTube", "Social")),
    ("youtube.com", ("youtube", "YouTube", "Social")),
    ("youtu.be", ("youtube", "YouTube", "Social")),
    ("android.gm", ("gmail", "Gmail", "Messaging")),
    ("mail.google", ("gmail", "Gmail", "Messaging")),
    ("chat.google", ("google-chat", "Google Chat", "Messaging")),
    ("classroom.google", ("google-classroom", "Google Classroom", "Education")),
    ("whatsapp", ("whatsapp", "WhatsApp", "Messaging")),
    ("wa.me", ("whatsapp", "WhatsApp", "Messaging")),
    ("telegram", ("telegram", "Telegram", "Messaging")),
    ("t.me", ("telegram", "Telegram", "Messaging")),
    ("instagram", ("instagram", "Instagram", "Social")),
    ("facebook", ("facebook", "Facebook", "Social")),
    ("fb.com", ("facebook", "Facebook", "Social")),
    ("messenger", ("facebook", "Facebook", "Social")),
    ("linkedin", ("linkedin", "LinkedIn", "Social")),
    ("t.co", ("x", "X / Twitter", "Social")),
    ("twitter", ("x", "X / Twitter", "Social")),
    ("x.com", ("x", "X / Twitter", "Social")),
    ("chatgpt", ("chatgpt", "ChatGPT", "AI assistants")),
    ("openai", ("chatgpt", "ChatGPT", "AI assistants")),
    ("perplexity", ("perplexity", "Perplexity", "AI assistants")),
    ("gemini.google", ("gemini", "Gemini", "AI assistants")),
    ("webqr", ("qr-website", "Online QR scanner website", "QR scanner apps")),
    ("qrcode", ("qr-website", "Online QR scanner website", "QR scanner apps")),
    ("scanqr", ("qr-website", "Online QR scanner website", "QR scanner apps")),
    ("bing.", ("bing", "Bing search", "Search")),
    ("duckduckgo", ("duckduckgo", "DuckDuckGo", "Search")),
    ("yahoo.", ("yahoo", "Yahoo search", "Search")),
)

_NO_REFERRER = ("direct", "Camera scan or app link (not reported)", "Not reported")


@lru_cache(maxsize=4096)
def _classify_cached(platform: str, confidence: str, referrer_host: str) -> tuple[str, str, str, str]:
    r = classify_source(platform, confidence, referrer_host)
    return r["channel"], r["label"], r["group"], r["how"]


def classify_source(platform: str | None, confidence: str | None, referrer_host: str | None) -> dict[str, str]:
    """Return channel, label, group and how the source is known ("tagged", "detected", "not_reported")."""
    platform_text = str(platform or "").strip()
    host = str(referrer_host or "").strip().lower().removeprefix("www.")
    conf = str(confidence or "").strip().lower()

    if conf in {"exact", "tagged"} and platform_text:
        tag = platform_text.lower()
        if tag in _TAGS:
            channel, label, group = _TAGS[tag]
        else:
            channel, label, group = (tag[:40], platform_text[:40], "Other tagged links")
        return {"channel": channel, "label": label, "group": group, "how": "tagged"}

    if host:
        for fragment, (channel, label, group) in _HOSTS:
            if fragment in host:
                return {"channel": channel, "label": label, "group": group, "how": "detected"}
        if host.startswith("google.") or ".google." in host or host == "google.com":
            return {"channel": "google-search", "label": "Google Search", "group": "Search", "how": "detected"}
        if host.count(".") >= 2 and host.split(".")[0] in {"com", "org", "net", "in", "io"}:
            # Android app id such as com.example.app
            return {"channel": f"app:{host}", "label": f"App · {host}", "group": "Other apps", "how": "detected"}
        return {"channel": f"site:{host}", "label": host, "group": "Websites", "how": "detected"}

    # Old rows stored only a platform name (no referrer host) for some apps.
    tag = platform_text.lower()
    if conf == "detected" and tag in _TAGS:
        channel, label, group = _TAGS[tag]
        return {"channel": channel, "label": label, "group": group, "how": "detected"}
    if conf == "detected" and tag == "google":
        return {"channel": "google", "label": "Google (app or search)", "group": "Search", "how": "detected"}
    channel, label, group = _NO_REFERRER
    return {"channel": channel, "label": label, "group": group, "how": "not_reported"}


_NETWORKS = (
    ("jio", "Jio"), ("reliance", "Jio"), ("airtel", "Airtel"), ("bharti", "Airtel"),
    ("vodafone", "Vi (Vodafone Idea)"), ("idea cellular", "Vi (Vodafone Idea)"),
    ("bsnl", "BSNL"), ("bharat sanchar", "BSNL"), ("mtnl", "MTNL"),
    ("atria convergence", "ACT Fibernet"), ("hathway", "Hathway"), ("tata", "Tata"),
    ("google", "Google"), ("microsoft", "Microsoft"), ("amazon", "Amazon"), ("cloudflare", "Cloudflare"),
)


def network_name(as_org: str | None) -> str:
    raw = str(as_org or "").strip()
    if not raw:
        return "Not reported"
    low = raw.lower()
    for fragment, name in _NETWORKS:
        if fragment in low:
            return name
    return raw[:48]


# --------------------------------------------------------------------------
# Location memo
# --------------------------------------------------------------------------
# Location sits inside each scan's telemetry JSON. Parsing that JSON for every scan
# on every refresh was the slow part (seconds). Scans never change after they are
# written, so each scan's (state, city, network) is read once and remembered as a
# small number per scan id (4 bytes each; 1 million scans is about 4 MB).
class _GeoMemo:
    def __init__(self) -> None:
        self.keys: list[tuple[str, str, str]] = [("", "", "")]
        self.index: dict[tuple[str, str, str], int] = {("", "", ""): 0}
        self.codes = array("i")
        self.max_id = 0
        self.lock = threading.Lock()

    def refresh(self, database: Any) -> None:
        with self.lock:
            edge = "CASE WHEN json_valid(telemetry_json) THEN json_extract(telemetry_json,'$.edge.{0}') END"
            with database.connect() as connection:
                rows = connection.execute(
                    f"SELECT id,{edge.format('region')},{edge.format('city')},{edge.format('asOrganization')} "
                    "FROM qr_scans WHERE id>? ORDER BY id",
                    (self.max_id,),
                ).fetchall()
            for row in rows:
                scan_id = int(row[0])
                key = (str(row[1] or "").strip(), str(row[2] or "").strip(), network_name(row[3]) if row[3] else "")
                code = self.index.get(key)
                if code is None:
                    code = len(self.keys)
                    self.keys.append(key)
                    self.index[key] = code
                if scan_id >= len(self.codes):
                    self.codes.extend([0] * (scan_id + 1 - len(self.codes)))
                self.codes[scan_id] = code
                self.max_id = max(self.max_id, scan_id)

    def get(self, scan_id: int) -> tuple[str, str, str]:
        if 0 <= scan_id < len(self.codes):
            return self.keys[self.codes[scan_id]]
        return ("", "", "")


_GEO: dict[str, _GeoMemo] = {}
_GEO_LOCK = threading.Lock()


def _geo(database: Any) -> _GeoMemo:
    key = str(database.path)
    with _GEO_LOCK:
        memo = _GEO.get(key)
        if memo is None:
            memo = _GEO[key] = _GeoMemo()
    memo.refresh(database)
    return memo


# --------------------------------------------------------------------------
# Computation
# --------------------------------------------------------------------------
def _ist_day_start_utc(day: date) -> str:
    return datetime(day.year, day.month, day.day, tzinfo=IST).astimezone(UTC).isoformat()


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _top(counter: Counter, limit: int, key: str = "label") -> list[dict[str, Any]]:
    return [{key: name, "scans": count} for name, count in counter.most_common(limit)]


def _scope(period: str, qr_id: str) -> tuple[list[str], list[Any], date | None, int | None, date]:
    today = datetime.now(IST).date()
    days = PERIOD_DAYS[period]
    start_day = today - timedelta(days=days - 1) if days else None
    where = ["s.confirmed=1", "s.device_type!='bot'"]
    params: list[Any] = []
    if start_day:
        where.append("s.scanned_at>=?")
        params.append(_ist_day_start_utc(start_day))
    if qr_id:
        where.append("s.qr_id=?")
        params.append(qr_id)
    return where, params, start_day, days, today


def _ist_text(value: str | None) -> str:
    moment = _parse_utc(value or "")
    return moment.astimezone(IST).strftime("%d %b %Y, %I:%M %p") if moment else ""


def compute_full(period: str, qr_id: str) -> dict[str, Any]:
    database = get_database()
    where, params, start_day, days, today = _scope(period, qr_id)

    with database.connect() as connection:
        qr_name = None
        if qr_id:
            row = connection.execute("SELECT name FROM qr_codes WHERE id=?", (qr_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="QR code not found")
            qr_name = str(row["name"])
        rows = connection.execute(
            f"""SELECT s.id,s.qr_id,s.scanned_at,s.visitor_hash,s.country,s.device_type,s.browser,
                       s.operating_system,s.platform,s.source_confidence,s.referrer_host,s.language
                FROM qr_scans s WHERE {' AND '.join(where)}""",
            tuple(params),
        ).fetchall()
        previous_scans = None
        if start_day and days:
            prev_start = start_day - timedelta(days=days)
            prev_params: list[Any] = [_ist_day_start_utc(prev_start), _ist_day_start_utc(start_day)]
            prev_sql = "SELECT COUNT(*) FROM qr_scans s WHERE s.confirmed=1 AND s.device_type!='bot' AND s.scanned_at>=? AND s.scanned_at<?"
            if qr_id:
                prev_sql += " AND s.qr_id=?"
                prev_params.append(qr_id)
            previous_scans = int(connection.execute(prev_sql, tuple(prev_params)).fetchone()[0])
        names = {str(r["id"]): str(r["name"]) for r in connection.execute("SELECT id,name FROM qr_codes").fetchall()}
    geo = _geo(database)

    daily: Counter = Counter()
    daily_visitors: dict[str, set[str]] = defaultdict(set)
    hours = [0] * 24
    weekdays = [0] * 7
    visitors: Counter = Counter()
    sources: dict[str, dict[str, Any]] = {}
    how: Counter = Counter()
    countries: Counter = Counter()
    states: Counter = Counter()
    cities: Counter = Counter()
    networks: Counter = Counter()
    devices: Counter = Counter()
    systems: Counter = Counter()
    browsers: Counter = Counter()
    languages: Counter = Counter()
    per_qr: Counter = Counter()
    places: dict[tuple[str, str, str], dict[str, Any]] = {}
    located = 0
    first_day: date | None = None

    for row in rows:
        scanned_at = str(row["scanned_at"])
        moment = _parse_utc(scanned_at)
        if moment is None:
            continue
        local = moment.astimezone(IST)
        day = local.date()
        first_day = day if first_day is None or day < first_day else first_day
        key = day.isoformat()
        daily[key] += 1
        visitor = str(row["visitor_hash"] or "")
        if visitor:
            daily_visitors[key].add(visitor)
            visitors[visitor] += 1
        hours[local.hour] += 1
        weekdays[local.weekday()] += 1

        channel, label, group, known = _classify_cached(str(row["platform"] or ""), str(row["source_confidence"] or ""), str(row["referrer_host"] or ""))
        entry = sources.get(channel)
        if entry is None:
            entry = sources[channel] = {"channel": channel, "label": label, "group": group, "how": known, "scans": 0, "hosts": Counter()}
        entry["scans"] += 1
        if row["referrer_host"]:
            entry["hosts"][str(row["referrer_host"])] += 1
        how[known] += 1

        country = str(row["country"] or "").strip() or "Unknown"
        countries[country] += 1
        region, city, network = geo.get(int(row["id"]))
        if region:
            states[f"{region}|{country}"] += 1
            located += 1
        if city:
            cities[f"{city}|{region}|{country}"] += 1
        networks[network or "Not reported"] += 1
        place_key = (country, region or "Not reported", city or "Not reported")
        place = places.get(place_key)
        if place is None:
            place = places[place_key] = {"scans": 0, "devices": set(), "networks": Counter(), "last": ""}
        place["scans"] += 1
        if visitor:
            place["devices"].add(visitor)
        if network:
            place["networks"][network] += 1
        if scanned_at > place["last"]:
            place["last"] = scanned_at
        devices[str(row["device_type"] or "Other")] += 1
        systems[str(row["operating_system"] or "Other")] += 1
        browsers[str(row["browser"] or "Other")] += 1
        language = str(row["language"] or "").strip()
        languages[language.split("-")[0].lower() if language else "Not reported"] += 1
        per_qr[str(row["qr_id"])] += 1

    total = len(rows)
    trend: list[dict[str, Any]] = []
    if total:
        cursor = start_day or first_day or today
        while cursor <= today:
            k = cursor.isoformat()
            trend.append({"day": k, "scans": daily.get(k, 0), "unique": len(daily_visitors.get(k, ()))})
            cursor += timedelta(days=1)
    returning = sum(1 for count in visitors.values() if count > 1)

    def pct(value: int) -> float:
        return round(value * 100.0 / total, 1) if total else 0.0

    source_rows = [{
        "channel": e["channel"], "label": e["label"], "group": e["group"], "how": e["how"],
        "scans": e["scans"], "share": pct(e["scans"]),
        "hosts": [{"host": h, "scans": c} for h, c in e["hosts"].most_common(3)],
    } for e in sorted(sources.values(), key=lambda item: item["scans"], reverse=True)]

    location_rows = []
    for (country, state, city), place in sorted(places.items(), key=lambda item: item[1]["scans"], reverse=True):
        top_network = place["networks"].most_common(1)
        location_rows.append({
            "country": country, "state": state, "city": city, "scans": place["scans"],
            "devices": len(place["devices"]), "share": pct(place["scans"]),
            "network": top_network[0][0] if top_network else "Not reported",
            "last_scan": place["last"],
        })

    overview = {
        "period": period,
        "qr_id": qr_id or None,
        "qr_name": qr_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "timezone": "Asia/Kolkata",
        "totals": {
            "scans": total,
            "unique_devices": len(visitors),
            "returning_devices": returning,
            "returning_share": round(returning * 100.0 / len(visitors), 1) if visitors else 0.0,
            "scans_per_device": round(total / len(visitors), 2) if visitors else 0.0,
            "today": daily.get(today.isoformat(), 0),
            "yesterday": daily.get((today - timedelta(days=1)).isoformat(), 0),
            "previous_period_scans": previous_scans,
            "change_pct": (round((total - previous_scans) * 100.0 / previous_scans, 1) if previous_scans else None),
            "active_days": sum(1 for value in daily.values() if value),
            "peak_day": max(daily.items(), key=lambda item: item[1])[0] if daily else None,
            "peak_day_scans": max(daily.values()) if daily else 0,
        },
        "trend": trend,
        "hours": hours,
        "weekdays": weekdays,
        "sources": source_rows,
        "source_quality": {
            "tagged": how.get("tagged", 0), "detected": how.get("detected", 0),
            "not_reported": how.get("not_reported", 0),
            "known_share": pct(how.get("tagged", 0) + how.get("detected", 0)),
        },
        "countries": [{"code": code, "scans": count, "share": pct(count)} for code, count in countries.most_common(30)],
        "states": [{"state": k.split("|")[0], "country": k.split("|")[1], "scans": c, "share": pct(c)} for k, c in states.most_common(40)],
        "cities": [{"city": k.split("|")[0], "state": k.split("|")[1], "country": k.split("|")[2], "scans": c} for k, c in cities.most_common(40)],
        "networks": _top(networks, 12),
        "devices": _top(devices, 8),
        "operating_systems": _top(systems, 8),
        "browsers": _top(browsers, 10),
        "languages": _top(languages, 10),
        "top_qr_codes": [] if qr_id else [{"id": i, "name": names.get(i, "Deleted QR"), "scans": c} for i, c in per_qr.most_common(10)],
        "location_count": len(location_rows),
        "accuracy": {
            "location_coverage": pct(located),
            "location": "Network location from Cloudflare. Country and state are reliable. City is the internet provider's city; on Indian mobile data it is often the operator's hub city, not the exact place of the phone.",
            "devices": "Unique devices are browser profiles on phones/computers, not people. Two browsers on one phone count twice.",
            "sources": "Detected automatically from the same single QR link: the app's built-in browser (Instagram, Facebook, Snapchat, LinkedIn…) or the app/website the phone reports (Google Lens, WhatsApp on Android, YouTube, Gmail, Google Search…). Phone-camera scans and some apps report nothing and are shown as Not reported. Tagged = an older link that carried ?src=….",
            "verified": "Only verified human scans: the scan page loaded and reported back. Bots and link previews are excluded.",
        },
    }
    return {"overview": overview, "locations": location_rows}


def compute_overview(period: str, qr_id: str) -> dict[str, Any]:
    return compute_full(period, qr_id)["overview"]


# --------------------------------------------------------------------------
# Cache: answer instantly, refresh in the background
# --------------------------------------------------------------------------
_KEY_LOCKS: dict[tuple[str, str, str], threading.Lock] = {}
_REFRESHING: set[tuple[str, str, str]] = set()


def _store(key: tuple[str, str, str], value: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        if len(_CACHE) > 128:
            _CACHE.clear()
        _CACHE[key] = (time.monotonic(), value)


def _compute_into_cache(key: tuple[str, str, str]) -> dict[str, Any]:
    with _CACHE_LOCK:
        lock = _KEY_LOCKS.setdefault(key, threading.Lock())
    with lock:
        cached = _CACHE.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
        value = compute_full(key[1], key[2])
        _store(key, value)
        return value


def _refresh_in_background(key: tuple[str, str, str]) -> None:
    with _CACHE_LOCK:
        if key in _REFRESHING:
            return
        _REFRESHING.add(key)

    def run() -> None:
        try:
            _compute_into_cache(key)
        except Exception:
            pass
        finally:
            with _CACHE_LOCK:
                _REFRESHING.discard(key)

    threading.Thread(target=run, name="qr-insights-refresh", daemon=True).start()


def _full(period: str, qr_id: str) -> dict[str, Any]:
    key = (str(get_database().path), period, qr_id)
    cached = _CACHE.get(key)
    if cached:
        if time.monotonic() - cached[0] >= _CACHE_TTL_SECONDS:
            _refresh_in_background(key)  # serve the last result now; fresh numbers follow
        return cached[1]
    return _compute_into_cache(key)


def prewarm() -> None:
    """Keep the common views ready so nobody waits (called every minute at startup)."""
    database = get_database()
    for period in ("30d", "7d", "90d", "all"):
        key = (str(database.path), period, "")
        try:
            value = compute_full(period, "")
            _store(key, value)
        except Exception:
            pass


async def prewarm_loop() -> None:
    import asyncio

    await asyncio.sleep(20)
    while True:
        try:
            await asyncio.to_thread(prewarm)
        except Exception:
            pass
        await asyncio.sleep(55)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@router.get("/overview")
def overview(
    period: Literal["7d", "30d", "90d", "365d", "all"] = Query("30d"),
    qr_id: str = Query("", max_length=120),
) -> dict[str, Any]:
    return copy.deepcopy(_full(period, qr_id)["overview"])


@router.get("/locations")
def locations(
    period: Literal["7d", "30d", "90d", "365d", "all"] = Query("30d"),
    qr_id: str = Query("", max_length=120),
) -> dict[str, Any]:
    full = _full(period, qr_id)
    return {"period": period, "qr_id": qr_id or None, "generated_at": full["overview"]["generated_at"],
            "total_scans": full["overview"]["totals"]["scans"], "items": copy.deepcopy(full["locations"])}


def _csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in {"=", "+", "-", "@"} else text


def _csv_response(header: list[str], rows: list[list[object]], filename: str) -> Response:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_csv_cell(v) for v in row])
    return Response(
        content="\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


def _file_tag(period: str, qr_id: str) -> str:
    return f"{period}{'-' + qr_id[:12] if qr_id else ''}-{datetime.now(IST).strftime('%Y%m%d-%H%M')}"


@router.get("/locations.csv")
def locations_csv(
    period: Literal["7d", "30d", "90d", "365d", "all"] = Query("30d"),
    qr_id: str = Query("", max_length=120),
) -> Response:
    items = _full(period, qr_id)["locations"]
    rows = [[i["country"], i["state"], i["city"], i["scans"], i["devices"], i["share"], i["network"], _ist_text(i["last_scan"])] for i in items]
    return _csv_response(
        ["Country", "State / Region", "City (approx., network city)", "Verified scans", "Unique devices", "Share %", "Main network", "Last scan (IST)"],
        rows, f"nexttoppers-qr-locations-{_file_tag(period, qr_id)}.csv",
    )


@router.get("/scans.csv")
def scans_csv(
    period: Literal["7d", "30d", "90d", "365d", "all"] = Query("30d"),
    qr_id: str = Query("", max_length=120),
) -> Response:
    database = get_database()
    where, params, _, _, _ = _scope(period, qr_id)
    with database.connect() as connection:
        rows = connection.execute(
            f"""SELECT s.id,s.scanned_at,q.name AS qr_name,s.country,s.device_type,s.operating_system,s.browser,
                       s.platform,s.source_confidence,s.referrer_host,s.language,s.visitor_hash,s.scanner_email
                FROM qr_scans s LEFT JOIN qr_codes q ON q.id=s.qr_id
                WHERE {' AND '.join(where)} ORDER BY s.id DESC""",
            tuple(params),
        ).fetchall()
    geo = _geo(database)
    out: list[list[object]] = []
    for row in rows:
        region, city, network = geo.get(int(row["id"]))
        _, label, _, known = _classify_cached(str(row["platform"] or ""), str(row["source_confidence"] or ""), str(row["referrer_host"] or ""))
        out.append([
            _ist_text(row["scanned_at"]), row["qr_name"] or "Deleted QR", row["country"], region, city, network,
            label, {"tagged": "Tagged", "detected": "Detected", "not_reported": "Not reported"}.get(known, known),
            row["referrer_host"], row["device_type"], row["operating_system"], row["browser"], row["language"],
            f"Device {str(row['visitor_hash'] or '')[:8].upper()}", row["scanner_email"] or "",
        ])
    return _csv_response(
        ["Scanned at (IST)", "QR code", "Country", "State / Region", "City (approx.)", "Network", "Source",
         "How source is known", "Referrer", "Device", "Operating system", "Browser", "Language", "Device ID", "Email (if given)"],
        out, f"nexttoppers-qr-scans-{_file_tag(period, qr_id)}.csv",
    )
