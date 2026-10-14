from __future__ import annotations

import pytest

from app.services.google_sheets import (
    InvalidGoogleSheetUrl,
    extract_spreadsheet_id,
    public_xlsx_export_url,
)


def test_extract_spreadsheet_id_from_normal_url() -> None:
    url = "https://docs.google.com/spreadsheets/d/abcDEF_123-xyz/edit#gid=0"
    assert extract_spreadsheet_id(url) == "abcDEF_123-xyz"


def test_extract_spreadsheet_id_from_query_url() -> None:
    url = "https://docs.google.com/open?id=abcDEF_123-xyz"
    assert extract_spreadsheet_id(url) == "abcDEF_123-xyz"


def test_invalid_google_sheet_url() -> None:
    with pytest.raises(InvalidGoogleSheetUrl):
        extract_spreadsheet_id("not-a-url")


def test_export_url() -> None:
    assert public_xlsx_export_url("abc") == (
        "https://docs.google.com/spreadsheets/d/abc/export?format=xlsx"
    )
