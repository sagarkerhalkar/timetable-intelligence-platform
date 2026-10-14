from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from ..models import ContentItem, ContentType, TestRecord
from ..timezones import INDIA_TIMEZONE
from ..utils import normalize_search_text, normalize_text, stable_hash
from .official_parser import canonical_subject
from .workbook_analyzer import detect_class, detect_stream

_HEADER_CLEAN_RE = re.compile(r"[^a-z0-9]+")
_DONE_RE = re.compile(r"\b(done|complete|completed|uploaded|live|yes|ok)\b", re.I)

_FILE_PLACEHOLDERS = {"", "-", "--", "done", "on app", "ok", "yes", "no", "pending", "uploaded", "live", "n a", "na"}

def _usable_file_value(title: str | None, url: str | None, kind: str) -> bool:
    if url:
        return True
    value = normalize_text(title).casefold()
    if not value or value in _FILE_PLACEHOLDERS:
        return False
    if kind == "pdf":
        return ".pdf" in value or value.endswith(" pdf") or "pdf file" in value
    return len(value) >= 4


HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "created_date": ("dates", "created date", "f"),
    "course": ("course", "cource", "course name", "cource name"),
    "class_name": ("class", "class subject", "class subject name"),
    "board": ("board",),
    "subject": ("subject",),
    "chapter_number": ("chapter number", "chapter no", "paper no", "test no 1"),
    "topic": ("chapter name", "topic", "lesson", "149"),
    "made_by": ("made by", "prepared by", "teacher", "faculty"),
    "questions": ("no of question", "no of que", "total questions", "questions"),
    "duration": ("test timing", "test timing in minutes", "duration"),
    "marks": ("test marks", "marks"),
    "document": ("docs link", "doc link", "document link", "link"),
    "pdf": ("pdf", "pdf link"),
    "app_status": ("app status", "status in website", "website status"),
    "test_date_status": ("test date",),
    "result_dashboard": ("result dashboard", "result deshbord", "result status"),
    "video_solution_update": ("video solution update", "video solution upodat", "video solution status"),
    "remarks": ("remark", "remarks", "raw files"),
}


def _clean_header(value: object) -> str:
    text = normalize_text(value).casefold()
    text = text.replace("&", " and ")
    return _HEADER_CLEAN_RE.sub(" ", text).strip()


def _match_field(header: str) -> str | None:
    if not header:
        return None
    for field, aliases in HEADER_ALIASES.items():
        if header in aliases:
            return field
    # Conservative contains matching for headings with spelling or line-break noise.
    if "result" in header and ("dashboard" in header or "deshbord" in header):
        return "result_dashboard"
    if "video" in header and "solution" in header:
        return "video_solution_update"
    if "app" in header and "status" in header:
        return "app_status"
    if "status" in header and "website" in header:
        return "app_status"
    if "docs" in header and "link" in header:
        return "document"
    if header.startswith("pdf"):
        return "pdf"
    if "chapter" in header and "name" in header:
        return "topic"
    if "chapter" in header and ("number" in header or " no" in f" {header}"):
        return "chapter_number"
    if "made by" in header or "prepared by" in header:
        return "made_by"
    if "question" in header:
        return "questions"
    if "timing" in header or "duration" in header:
        return "duration"
    return None


def _header_map(worksheet: Worksheet) -> tuple[int, dict[str, int]] | None:
    best: tuple[int, int, dict[str, int]] | None = None
    max_scan = min(30, worksheet.max_row)
    for row_number in range(1, max_scan + 1):
        mapping: dict[str, int] = {}
        date_columns: list[int] = []
        for column in range(1, worksheet.max_column + 1):
            header = _clean_header(worksheet.cell(row_number, column).value)
            if not header:
                continue
            if header in {"date", "dates"}:
                date_columns.append(column)
                continue
            field = _match_field(header)
            if field and field not in mapping:
                mapping[field] = column
        if date_columns:
            mapping.setdefault("created_date", date_columns[0])
            if len(date_columns) > 1:
                mapping.setdefault("test_date_status", date_columns[-1])
        # The live PRARAMBH tab currently uses a numeric heading (149) for topic.
        if "topic" not in mapping and "chapter_number" in mapping:
            next_column = mapping["chapter_number"] + 1
            if next_column <= worksheet.max_column:
                mapping["topic"] = next_column
        score = len(mapping)
        if "document" in mapping:
            score += 4
        if "subject" in mapping:
            score += 2
        if "class_name" in mapping:
            score += 2
        if best is None or score > best[0]:
            best = (score, row_number, mapping)
    if best is None or best[0] < 5:
        return None
    mapping = best[2]
    strong_status = any(field in mapping for field in (
        "app_status", "result_dashboard", "video_solution_update"
    ))
    structured_test = "document" in mapping and any(field in mapping for field in (
        "questions", "marks", "course", "chapter_number"
    ))
    if not (strong_status or structured_test):
        return None
    return best[1], mapping


def _cell_text(worksheet: Worksheet, row: int, column: int | None) -> str | None:
    if not column:
        return None
    value = normalize_text(worksheet.cell(row, column).value)
    return value or None


def _cell_link(worksheet: Worksheet, row: int, column: int | None) -> tuple[str | None, str | None, str | None]:
    if not column:
        return None, None, None
    cell = worksheet.cell(row, column)
    title = normalize_text(cell.value) or None
    url = cell.hyperlink.target if cell.hyperlink and cell.hyperlink.target else None
    return title, url, cell.coordinate


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    if not text:
        return None
    text = re.sub(r"\b(done|completed?)\b", "", text, flags=re.I).strip(" -")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in (
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def status_is_done(value: str | None) -> bool:
    return bool(value and _DONE_RE.search(value))


def _record_added_at(record: TestRecord) -> datetime | None:
    """Best available timestamp for assigning a test to a weekly cycle.

    New rows use the exact first-seen time. Baseline rows have a 1970 marker,
    so their Sheet-created date is used at noon as a safe fallback.
    """
    if record.first_seen_at and record.first_seen_at.year > 1971:
        value = record.first_seen_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(INDIA_TIMEZONE)
    if record.created_date:
        return datetime.combine(record.created_date, time(12, 0), tzinfo=INDIA_TIMEZONE)
    return None


def weekly_cycle(now: datetime | None = None) -> tuple[datetime, datetime, date, datetime, datetime]:
    """Return Monday 09:00 -> Saturday 18:00 and its Sunday deadlines."""
    current = (now or datetime.now(INDIA_TIMEZONE)).astimezone(INDIA_TIMEZONE)
    days_to_sunday = (6 - current.weekday()) % 7
    sunday = current.date() + timedelta(days=days_to_sunday)
    monday = sunday - timedelta(days=6)
    window_start = datetime.combine(monday, time(9, 0), tzinfo=INDIA_TIMEZONE)
    window_end = datetime.combine(sunday - timedelta(days=1), time(18, 0), tzinfo=INDIA_TIMEZONE)
    result_deadline = datetime.combine(sunday + timedelta(days=1), time(18, 0), tzinfo=INDIA_TIMEZONE)
    video_deadline = datetime.combine(sunday + timedelta(days=2), time(18, 0), tzinfo=INDIA_TIMEZONE)
    return window_start, window_end, sunday, result_deadline, video_deadline


def assigned_test_sunday(record: TestRecord) -> date | None:
    # An explicit Test Date is the strongest signal, but operations are Sunday-based.
    # Any Monday-Saturday date belongs to the Sunday ending that same calendar week.
    # An explicit Sunday remains unchanged. This keeps the original source date on the
    # record while placing it in the correct Sunday readiness cycle.
    explicit = _parse_date(record.test_date_status)
    if explicit:
        return explicit + timedelta(days=(6 - explicit.weekday()) % 7)
    added_at = _record_added_at(record)
    if added_at is None:
        return None
    monday = added_at.date() - timedelta(days=added_at.weekday())
    start = datetime.combine(monday, time(9, 0), tzinfo=INDIA_TIMEZONE)
    end = datetime.combine(monday + timedelta(days=5), time(18, 0), tzinfo=INDIA_TIMEZONE)
    if start <= added_at <= end:
        return monday + timedelta(days=6)
    return None


def tests_for_sunday(records: Iterable[TestRecord], sunday: date) -> list[TestRecord]:
    return [record for record in records if assigned_test_sunday(record) == sunday]


def test_is_due(record: TestRecord, today: date | None = None) -> bool:
    today = today or datetime.now(INDIA_TIMEZONE).date()
    status = normalize_text(record.test_date_status)
    if status_is_done(status):
        return True
    assigned = assigned_test_sunday(record)
    return bool(assigned and assigned <= today)


def _subject(value: str | None) -> str | None:
    if not value:
        return None
    return canonical_subject(value) or normalize_text(value)


def _record_identity(record: TestRecord) -> str:
    anchor = record.document_url or record.document_title or record.pdf_url or record.pdf_title
    if not anchor:
        anchor = "|".join(
            value for value in (
                record.course, record.class_name, record.subject, record.chapter_number, record.topic
            ) if value
        )
    return stable_hash(
        "test-record", record.source_id, record.sheet_name,
        normalize_search_text(anchor), record.source_row,
    )


def _content_type(title: str | None, url: str | None, kind: str) -> ContentType:
    text = f"{title or ''} {url or ''}".casefold()
    if kind == "pdf" or ".pdf" in text:
        return ContentType.PDF
    if any(ext in text for ext in (".ppt", ".pptx")):
        return ContentType.PRESENTATION
    if any(ext in text for ext in (".xls", ".xlsx", "docs.google.com/spreadsheets")):
        return ContentType.SPREADSHEET
    return ContentType.DOCUMENT


def _record_to_content(record: TestRecord) -> list[ContentItem]:
    items: list[ContentItem] = []
    entries = [
        ("document", record.document_title, record.document_url, record.source_coordinates[0] if record.source_coordinates else f"A{record.source_row}"),
        ("pdf", record.pdf_title, record.pdf_url, record.source_coordinates[-1] if record.source_coordinates else f"A{record.source_row}"),
    ]
    for kind, title, url, coordinate in entries:
        if not title and not url:
            continue
        display_title = title or f"{record.subject or 'Test'} - {record.topic or record.chapter_number or 'paper'}"
        search_text = " ".join(
            value for value in (
                record.workbook_name, record.sheet_name, record.course, record.class_name, record.board,
                record.subject, record.chapter_number, record.topic, record.made_by, record.questions,
                record.duration, record.marks, display_title, record.app_status, record.test_date_status,
                record.result_dashboard, record.video_solution_update, record.remarks,
            ) if value
        )
        items.append(ContentItem(
            id=stable_hash("test-content", record.id, kind, url or display_title),
            source_id=record.source_id,
            workbook_name=record.workbook_name,
            sheet_name=record.sheet_name,
            coordinate=coordinate,
            source_row=record.source_row,
            url=url or "",
            title=display_title,
            content_type=_content_type(title, url, kind),
            stream=detect_stream(" ".join(value for value in (record.course, record.class_name, record.subject, record.topic) if value)),
            class_name=detect_class(record.class_name or "") or record.class_name,
            batch=record.course,
            subject=record.subject,
            topic=record.topic or record.chapter_number,
            teacher=record.made_by,
            search_text=search_text,
            confidence=0.99 if url else 0.88,
            warnings=[] if url else ["File name is present but the Google Sheet cell has no clickable link"],
            fingerprint=stable_hash(record.source_id, record.sheet_name, record.source_row, kind, url or display_title),
            record_kind="test",
            status=record.app_status,
            test_number=record.chapter_number,
            test_date=record.test_date_status,
            result_dashboard=record.result_dashboard,
            video_solution_update=record.video_solution_update,
            questions=record.questions,
            duration=record.duration,
            marks=record.marks,
            remarks=record.remarks,
        ))
    return items


def parse_test_workbook(
    workbook_path: Path,
    *,
    source_id: str,
    workbook_name: str,
) -> tuple[list[TestRecord], list[ContentItem]]:
    workbook_input = workbook_path if workbook_path.suffix.lower() in {".xlsx", ".xlsm", ".xltx", ".xltm"} else BytesIO(workbook_path.read_bytes())
    workbook = load_workbook(workbook_input, data_only=False, read_only=False)
    records: list[TestRecord] = []
    content: list[ContentItem] = []
    for worksheet in workbook.worksheets:
        header_result = _header_map(worksheet)
        if header_result is None:
            continue
        header_row, columns = header_result
        for row in range(header_row + 1, worksheet.max_row + 1):
            document_title, document_url, document_coordinate = _cell_link(worksheet, row, columns.get("document"))
            pdf_title, pdf_url, pdf_coordinate = _cell_link(worksheet, row, columns.get("pdf"))
            if not _usable_file_value(document_title, document_url, "document"):
                document_title, document_url, document_coordinate = None, None, None
            if not _usable_file_value(pdf_title, pdf_url, "pdf"):
                pdf_title, pdf_url, pdf_coordinate = None, None, None
            subject = _subject(_cell_text(worksheet, row, columns.get("subject")))
            topic = _cell_text(worksheet, row, columns.get("topic"))
            class_name = _cell_text(worksheet, row, columns.get("class_name"))
            course = _cell_text(worksheet, row, columns.get("course"))
            # A row is a test record when it has a file/name or enough academic fields.
            academic_values = [subject, topic, class_name, course, _cell_text(worksheet, row, columns.get("chapter_number"))]
            if not (document_title or document_url or pdf_title or pdf_url or sum(bool(v) for v in academic_values) >= 3):
                continue
            if document_title and document_title.casefold() in {"docs link", "link"}:
                continue
            created_date = _parse_date(worksheet.cell(row, columns["created_date"]).value) if columns.get("created_date") else None
            coordinates = [value for value in (document_coordinate, pdf_coordinate) if value]
            record = TestRecord(
                id="pending",
                source_id=source_id,
                workbook_name=workbook_name,
                sheet_name=worksheet.title,
                source_row=row,
                source_coordinates=coordinates,
                created_date=created_date,
                course=course,
                class_name=detect_class(class_name or "") or class_name,
                board=_cell_text(worksheet, row, columns.get("board")),
                subject=subject,
                chapter_number=_cell_text(worksheet, row, columns.get("chapter_number")),
                topic=topic,
                made_by=_cell_text(worksheet, row, columns.get("made_by")),
                questions=_cell_text(worksheet, row, columns.get("questions")),
                duration=_cell_text(worksheet, row, columns.get("duration")),
                marks=_cell_text(worksheet, row, columns.get("marks")),
                document_title=document_title,
                document_url=document_url,
                pdf_title=pdf_title,
                pdf_url=pdf_url,
                app_status=_cell_text(worksheet, row, columns.get("app_status")),
                test_date_status=_cell_text(worksheet, row, columns.get("test_date_status")),
                result_dashboard=_cell_text(worksheet, row, columns.get("result_dashboard")),
                video_solution_update=_cell_text(worksheet, row, columns.get("video_solution_update")),
                remarks=_cell_text(worksheet, row, columns.get("remarks")),
                search_text=None,
                fingerprint="pending",
            )
            record.id = _record_identity(record)
            record.fingerprint = stable_hash(
                record.source_id, record.sheet_name, record.source_row,
                record.document_url or record.document_title or record.pdf_url or record.pdf_title or record.id,
            )
            record.search_text = " ".join(
                value for value in (
                    record.workbook_name, record.sheet_name, record.course, record.class_name, record.board,
                    record.subject, record.chapter_number, record.topic, record.made_by, record.document_title,
                    record.pdf_title, record.app_status, record.test_date_status, record.result_dashboard,
                    record.video_solution_update, record.remarks,
                ) if value
            )
            records.append(record)
            content.extend(_record_to_content(record))
    # Exact row identity is unique. Keep the highest-information version if duplicated.
    unique_records = {record.id: record for record in records}
    unique_content = {item.id: item for item in content}
    return (
        sorted(unique_records.values(), key=lambda item: (item.sheet_name, item.source_row)),
        sorted(unique_content.values(), key=lambda item: (item.sheet_name, item.source_row, item.title)),
    )
