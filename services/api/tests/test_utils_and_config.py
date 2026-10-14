from __future__ import annotations

from datetime import date, time

import pytest

from app.config import Settings
from app.utils import compact_json, find_urls, first_non_empty, normalize_text, stable_hash


def test_utility_helpers() -> None:
    assert normalize_text(None) == ""
    assert normalize_text(2.0) == "2"
    assert normalize_text(date(2026, 8, 4)) == "2026-08-04"
    assert normalize_text(time(18, 30)) == "18:30:00"
    assert find_urls("Open https://example.com/file.pdf, now") == ["https://example.com/file.pdf"]
    assert first_non_empty([None, "  ", "value"]) == "value"
    assert first_non_empty([]) is None
    assert compact_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert stable_hash("same") == stable_hash("same")


def test_non_sqlite_database_url_rejected() -> None:
    settings = Settings(database_url="postgresql://localhost/example")
    with pytest.raises(ValueError):
        _ = settings.database_path
