from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

WORKER_NAME = os.environ.get("NEXTTOPPERS_QR_WORKER_NAME", "q").strip() or "q"
ACCOUNT_ID = os.environ.get(
    "CLOUDFLARE_ACCOUNT_ID",
    "7568b005c1ad536426ee8a2af8ba43f4",
).strip()
BINDING_NAME = "QR_EDGE"
CACHE_SECONDS = 600

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_CACHE_FILE = _DATA_DIR / "qr_edge_runtime.json"
_LOG_FILE = _DATA_DIR / "qr_edge_sync.log"
_LOCK = Lock()
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_NAMESPACE_ID_RE = re.compile(r"^[0-9a-fA-F]{20,64}$")


class QrEdgeSyncError(RuntimeError):
    pass


def _log(message: str) -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        with _LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except Exception:
        pass


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _model_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        data = model_dump()
        return dict(data) if isinstance(data, dict) else {}
    return {}


def _wrangler_base() -> list[str]:
    direct = shutil.which("wrangler") or shutil.which("wrangler.cmd")
    if direct:
        return [direct]
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if npx:
        return [npx, "--yes", "wrangler@latest"]
    raise QrEdgeSyncError("Cloudflare Wrangler/npx is not installed on the QR server.")


def _run_wrangler(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if ACCOUNT_ID:
        env.setdefault("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    try:
        return subprocess.run(
            _wrangler_base() + args,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise QrEdgeSyncError(f"Cloudflare command timed out: {' '.join(args[:4])}") from exc


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout + "\n" + result.stderr).strip()


def _json_output(result: subprocess.CompletedProcess[str], label: str) -> Any:
    if result.returncode != 0:
        raise QrEdgeSyncError(f"{label} failed: {_combined(result)[-900:]}")
    text = result.stdout.strip()
    try:
        return json.loads(text)
    except Exception as exc:
        raise QrEdgeSyncError(f"{label} did not return valid JSON: {_combined(result)[-900:]}") from exc


def _collect_active_version_ids(value: Any, *, in_versions: bool = False) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            child_in_versions = in_versions or lower in {"versions", "version", "active_versions"}
            if isinstance(child, str) and _UUID_RE.fullmatch(child):
                if "version" in lower or child_in_versions:
                    found.add(child)
            else:
                found |= _collect_active_version_ids(child, in_versions=child_in_versions)
    elif isinstance(value, list):
        for child in value:
            found |= _collect_active_version_ids(child, in_versions=in_versions)
    return found


def _find_binding_namespace_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        binding_name = str(
            value.get("name")
            or value.get("binding")
            or value.get("variable_name")
            or value.get("binding_name")
            or ""
        )
        if binding_name == BINDING_NAME:
            for key in ("namespace_id", "id", "resource_id"):
                candidate = value.get(key)
                if isinstance(candidate, str) and _NAMESPACE_ID_RE.fullmatch(candidate):
                    found.add(candidate)
        for child in value.values():
            found |= _find_binding_namespace_ids(child)
    elif isinstance(value, list):
        for child in value:
            found |= _find_binding_namespace_ids(child)
    return found


def _existing_namespace_ids() -> set[str]:
    result = _run_wrangler(["kv", "namespace", "list"], 90)
    payload = _json_output(result, "Cloudflare KV namespace list")
    items = payload if isinstance(payload, list) else payload.get("result", []) if isinstance(payload, dict) else []
    found: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate = str(item.get("id") or item.get("namespace_id") or "")
        if _NAMESPACE_ID_RE.fullmatch(candidate):
            found.add(candidate)
    return found


def _discover_production_namespace_ids() -> list[str]:
    # IMPORTANT: only current production status is inspected.
    # Historical deployment/version lists are deliberately NOT used.
    status_result = _run_wrangler(
        ["deployments", "status", "--name", WORKER_NAME, "--json"],
        120,
    )
    status_payload = _json_output(status_result, "Current Worker deployment status")
    version_ids = _collect_active_version_ids(status_payload)
    if not version_ids:
        raise QrEdgeSyncError(
            "Could not identify the version currently serving production traffic for Worker q."
        )

    bound: set[str] = set()
    for version_id in sorted(version_ids):
        view_result = _run_wrangler(
            ["versions", "view", version_id, "--name", WORKER_NAME, "--json"],
            120,
        )
        if view_result.returncode != 0:
            _log(f"version view skipped {version_id}: {_combined(view_result)[-500:]}")
            continue
        try:
            view_payload = json.loads(view_result.stdout)
        except Exception:
            _log(f"version view invalid json {version_id}")
            continue
        bound |= _find_binding_namespace_ids(view_payload)

    if not bound:
        raise QrEdgeSyncError(
            "The currently deployed Worker version does not expose a QR_EDGE KV binding."
        )

    existing = _existing_namespace_ids()
    live = sorted(bound & existing)
    stale = sorted(bound - existing)
    if stale:
        _log(f"ignored stale/deleted production binding ids={stale}")
    if not live:
        raise QrEdgeSyncError(
            "QR_EDGE binding was found, but none of its KV namespaces exist in the Cloudflare account."
        )
    return live


def _read_cache() -> list[str]:
    try:
        payload = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        saved_at = float(payload.get("saved_at") or 0)
        ids = [str(x) for x in payload.get("namespace_ids", [])]
        if time.time() - saved_at <= CACHE_SECONDS and ids and all(_NAMESPACE_ID_RE.fullmatch(x) for x in ids):
            return ids
    except Exception:
        return []
    return []


def _write_cache(ids: list[str]) -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp = _CACHE_FILE.with_suffix(".json.new")
        temp.write_text(
            json.dumps({"saved_at": time.time(), "namespace_ids": ids}, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, _CACHE_FILE)
    except Exception as exc:
        _log(f"cache write ignored: {exc}")


def production_namespace_ids(*, force_refresh: bool = False) -> list[str]:
    with _LOCK:
        if not force_refresh:
            cached = _read_cache()
            if cached:
                return cached
        ids = _discover_production_namespace_ids()
        _write_cache(ids)
        _log(f"production QR_EDGE namespace ids={ids}")
        return ids


def _route_payload(record: Any, *, force_active: bool | None = None) -> dict[str, Any]:
    exp = _model_dict(_value(record, "experience", {}))
    active = bool(_value(record, "active", True))
    if force_active is not None:
        active = bool(force_active)
    return {
        "ok": True,
        "id": str(_value(record, "id", "")),
        "slug": str(_value(record, "slug", "")),
        "name": str(_value(record, "name", "NextToppers QR"))[:200],
        "qr_type": str(_value(record, "qr_type", "url"))[:40],
        "tracking_mode": str(_value(record, "tracking_mode", "tracked"))[:20],
        "identity_mode": str(_value(record, "identity_mode", "anonymous"))[:20],
        "target_url": str(_value(record, "target_url", ""))[:8000],
        "active": active,
        "experience": {
            "mode": str(exp.get("mode") or "brand")[:12],
            "asset_id": str(exp.get("asset_id"))[:80] if exp.get("asset_id") else None,
            "title": str(exp.get("title") or "NextToppers")[:80],
            "message": str(exp.get("message") or "Opening your content…")[:160],
            "accent_color": str(exp.get("accent_color") or "#2455FF")[:24],
            "background_color": str(exp.get("background_color") or "#F8FAFC")[:24],
            "redirect_delay_ms": max(0, min(120, int(exp.get("redirect_delay_ms") or 0))),
            "logo_scale_percent": max(15, min(65, int(exp.get("logo_scale_percent") or 28))),
            "image_fit": "contain" if exp.get("image_fit") == "contain" else "cover",
            "image_scale_percent": max(35, min(100, int(exp.get("image_scale_percent") or 100))),
        },
        "updated_at": str(_value(record, "updated_at", ""))[:80],
    }


def _parse_route_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    # Tolerate Wrangler informational lines around the JSON value.
    starts = [match.start() for match in re.finditer(r"\{", text)]
    for start in reversed(starts):
        try:
            payload = json.loads(text[start:])
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _put_and_verify(namespace_id: str, route: dict[str, Any]) -> None:
    """
    Write one QR route to Cloudflare KV without putting the JSON value on the
    Windows command line.

    URLs can contain shell metacharacters such as '&'.  Wrangler is often
    reached through npx.cmd on Windows, so an inline JSON VALUE can be split by
    cmd.exe before Wrangler sees --namespace-id.  --path avoids that entire
    quoting/shell problem and is also the documented Wrangler mechanism for
    reading a KV value from a file.
    """
    key = f"qr:{route['slug']}"
    value = json.dumps(route, ensure_ascii=True, separators=(",", ":"))
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="ntqr_kv_",
            suffix=".json",
            dir=_DATA_DIR,
            delete=False,
            newline="",
        ) as handle:
            handle.write(value)
            handle.flush()
            temp_path = Path(handle.name)

        put_result = _run_wrangler(
            [
                "kv", "key", "put",
                key,
                "--path", str(temp_path),
                f"--namespace-id={namespace_id}",
                "--remote",
            ],
            120,
        )
        if put_result.returncode != 0:
            raise QrEdgeSyncError(
                f"KV write failed for {namespace_id}: {_combined(put_result)[-900:]}"
            )
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception as exc:
                _log(f"temporary KV value file cleanup ignored: {exc}")

    # Workers KV is eventually consistent.  A successful write can be followed
    # briefly by a read of the previous cached value.  Do not roll back a good
    # QR edit just because the first read-after-write is stale.
    deadline = time.time() + 75
    last = ""
    last_readback = None
    while time.time() < deadline:
        attempts = [
            ["kv", "key", "get", key, f"--namespace-id={namespace_id}", "--remote", "--text"],
            ["kv", "key", "get", key, f"--namespace-id={namespace_id}", "--remote"],
        ]
        for args in attempts:
            get_result = _run_wrangler(args, 120)
            last = _combined(get_result)
            if get_result.returncode != 0:
                continue
            readback = _parse_route_json(get_result.stdout) or _parse_route_json(last)
            if not isinstance(readback, dict):
                continue
            last_readback = readback
            if (
                str(readback.get("slug") or "") == str(route["slug"])
                and str(readback.get("target_url") or "") == str(route["target_url"])
                and bool(readback.get("active")) == bool(route["active"])
            ):
                return
        time.sleep(3)

    if not isinstance(last_readback, dict):
        raise QrEdgeSyncError(f"KV readback failed for {namespace_id}: {last[-900:]}")
    raise QrEdgeSyncError(
        "KV write succeeded but the new value was not visible within 75 seconds "
        f"for {namespace_id}. last_target={last_readback.get('target_url')!r} "
        f"expected_target={route['target_url']!r}"
    )


def sync_qr_record(record: Any) -> None:
    if str(_value(record, "tracking_mode", "")) != "tracked":
        return
    slug = str(_value(record, "slug", "")).strip()
    target = str(_value(record, "target_url", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", slug):
        raise QrEdgeSyncError("QR edge sync received an invalid slug.")
    if not target:
        raise QrEdgeSyncError("QR edge sync received an empty target.")

    route = _route_payload(record)
    last_error: Exception | None = None
    for attempt in range(2):
        ids = production_namespace_ids(force_refresh=(attempt == 1))
        try:
            for namespace_id in ids:
                _put_and_verify(namespace_id, route)
            _log(f"SYNC OK slug={slug} active={route['active']} target={target}")
            return
        except Exception as exc:
            last_error = exc
            _log(f"SYNC RETRY slug={slug} attempt={attempt + 1} error={exc}")
    raise QrEdgeSyncError(f"Cloudflare edge sync failed for {slug}: {last_error}")


def sync_qr_records(records: Iterable[Any]) -> None:
    for record in records:
        sync_qr_record(record)


def deactivate_qr_record(record: Any) -> None:
    if str(_value(record, "tracking_mode", "")) != "tracked":
        return
    route = _route_payload(record, force_active=False)
    last_error: Exception | None = None
    for attempt in range(2):
        ids = production_namespace_ids(force_refresh=(attempt == 1))
        try:
            for namespace_id in ids:
                _put_and_verify(namespace_id, route)
            _log(f"DEACTIVATE OK slug={route['slug']}")
            return
        except Exception as exc:
            last_error = exc
            _log(f"DEACTIVATE RETRY slug={route['slug']} attempt={attempt + 1} error={exc}")
    raise QrEdgeSyncError(f"Cloudflare edge deactivation failed for {route['slug']}: {last_error}")


def status_snapshot() -> dict[str, Any]:
    ids = production_namespace_ids(force_refresh=True)
    return {
        "ok": True,
        "worker": WORKER_NAME,
        "binding": BINDING_NAME,
        "namespace_ids": ids,
        "cache_file": str(_CACHE_FILE),
        "log_file": str(_LOG_FILE),
    }
