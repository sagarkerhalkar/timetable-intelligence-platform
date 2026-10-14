from __future__ import annotations

from datetime import date, time
from io import BytesIO

from openpyxl import load_workbook

from app.models import TimetableEntry
from app.services.exports import build_timetable_pdf, build_timetable_xlsx


def entry() -> TimetableEntry:
    return TimetableEntry(
        id="one",
        source_id="source",
        workbook_name="Commerce",
        sheet_name="Time Table",
        source_row=2,
        source_coordinates=["A2", "B2"],
        class_date=date(2026, 8, 4),
        day="Tuesday",
        start_time=time(18, 30),
        end_time=time(19, 30),
        stream="Commerce",
        class_name="Class 12",
        subject="Economics",
        topic="National Income",
        confidence=0.9,
        fingerprint="fp",
    )


def test_xlsx_export() -> None:
    content = build_timetable_xlsx([entry()])
    workbook = load_workbook(BytesIO(content))
    sheet = workbook["Timetable"]
    assert sheet["A1"].value == "Date"
    assert sheet["G2"].value == "Economics"


def test_pdf_export() -> None:
    content = build_timetable_pdf([entry()])
    assert content.startswith(b"%PDF")
    assert len(content) > 1000
