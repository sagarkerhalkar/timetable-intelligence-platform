from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import parse_qs, urlparse

import httpx

SHEET_ID_PATTERNS = (
    re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)"),
    re.compile(r"[?&]id=([a-zA-Z0-9-_]+)"),
)


class InvalidGoogleSheetUrl(ValueError):
    pass


def extract_spreadsheet_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidGoogleSheetUrl("Google Sheet URL must use http or https")
    for pattern in SHEET_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    query_id = parse_qs(parsed.query).get("id")
    if query_id and query_id[0]:
        return query_id[0]
    raise InvalidGoogleSheetUrl("Could not find a spreadsheet ID in the supplied URL")


def public_xlsx_export_url(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"


async def download_public_workbook(
    spreadsheet_id: str,
    max_download_mb: int,
    timeout_seconds: int,
) -> Path:
    url = public_xlsx_export_url(spreadsheet_id)
    max_bytes = max_download_mb * 1024 * 1024
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "spreadsheet" not in content_type and "octet-stream" not in content_type:
                raise ValueError(
                    "Google did not return an XLSX file. The sheet may be private or access-restricted."
                )
            with NamedTemporaryFile(suffix=".xlsx", delete=False) as temporary:
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Workbook exceeds the {max_download_mb} MB safety limit")
                    temporary.write(chunk)
                return Path(temporary.name)
