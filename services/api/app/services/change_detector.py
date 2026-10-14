from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from ..models import CellSnapshot, ChangeRecord, ChangeType
from ..utils import normalize_text, stable_hash
from .sheet_schema import clean_header, match_field


def detect_cell_changes(
    previous: list[CellSnapshot],
    current: list[CellSnapshot],
    detected_at: datetime | None = None,
) -> list[ChangeRecord]:
    timestamp = detected_at or datetime.now(UTC)
    old = {cell.stable_key: cell for cell in previous}
    new = {cell.stable_key: cell for cell in current}
    context = _change_context(previous, current)
    changes: list[ChangeRecord] = []

    for key in sorted(new.keys() - old.keys()):
        cell = new[key]
        field_name, row_label = context.get((cell.sheet_name, cell.row, cell.column), (None, None))
        changes.append(_change(cell, ChangeType.ADDED, None, _display_value(cell), timestamp, field_name, row_label))

    for key in sorted(old.keys() - new.keys()):
        cell = old[key]
        field_name, row_label = context.get((cell.sheet_name, cell.row, cell.column), (None, None))
        changes.append(_change(cell, ChangeType.DELETED, _display_value(cell), None, timestamp, field_name, row_label))

    for key in sorted(old.keys() & new.keys()):
        before, after = old[key], new[key]
        # Daily history is about meaningful data changes. Formatting-only
        # edits are deliberately excluded so colour/font adjustments do not
        # flood the audit trail.
        before_signature = (before.value, before.formula, before.hyperlink)
        after_signature = (after.value, after.formula, after.hyperlink)
        if before_signature != after_signature:
            field_name, row_label = context.get((after.sheet_name, after.row, after.column), (None, None))
            changes.append(
                _change(
                    after,
                    ChangeType.UPDATED,
                    _display_value(before),
                    _display_value(after),
                    timestamp,
                    field_name,
                    row_label,
                )
            )

    return changes


def _change_context(
    previous: list[CellSnapshot], current: list[CellSnapshot]
) -> dict[tuple[str, int, int], tuple[str | None, str | None]]:
    """Resolve human field names and row identities before old cells are replaced."""

    cells_by_sheet: dict[str, dict[tuple[int, int], CellSnapshot]] = defaultdict(dict)
    # Current values are preferred, while previous values preserve context for removed rows.
    for cell in previous:
        cells_by_sheet[cell.sheet_name][(cell.row, cell.column)] = cell
    for cell in current:
        cells_by_sheet[cell.sheet_name][(cell.row, cell.column)] = cell

    result: dict[tuple[str, int, int], tuple[str | None, str | None]] = {}
    for sheet_name, grid in cells_by_sheet.items():
        max_column = max((column for _, column in grid), default=0)
        best_row: int | None = None
        best_score = -1
        semantic_columns: dict[int, str] = {}
        header_labels: dict[int, str] = {}
        for row in range(1, min(40, max((row for row, _ in grid), default=0)) + 1):
            row_semantic: dict[int, str] = {}
            row_labels: dict[int, str] = {}
            for column in range(1, max_column + 1):
                cell = grid.get((row, column))
                label = normalize_text(cell.value) if cell else ""
                field = match_field(clean_header(label))
                if field:
                    row_semantic[column] = field
                    row_labels[column] = label
            score = len(row_semantic)
            if score > best_score:
                best_score = score
                best_row = row if score else None
                semantic_columns = row_semantic
                header_labels = row_labels

        identity_order = (
            "course", "stream", "class_name", "subject", "chapter_number", "topic",
            "document", "pdf", "video", "presentation",
        )
        semantic_to_column = {field: column for column, field in semantic_columns.items()}
        all_rows = sorted({row for row, _ in grid})
        for row in all_rows:
            row_parts: list[str] = []
            for field in identity_order:
                column = semantic_to_column.get(field)
                cell = grid.get((row, column)) if column else None
                value = normalize_text(cell.value) if cell else ""
                if value and value not in row_parts:
                    row_parts.append(value)
                if len(row_parts) >= 4:
                    break
            row_label = " → ".join(row_parts) if row_parts else None
            if best_row and row == best_row:
                row_label = "Column headings"
            for column in range(1, max_column + 1):
                label = header_labels.get(column)
                if not label:
                    semantic = semantic_columns.get(column)
                    label = semantic.replace("_", " ").title() if semantic else f"Column {column}"
                result[(sheet_name, row, column)] = (label, row_label)
    return result


def _display_value(cell: CellSnapshot) -> str:
    """Show a human-readable value and preserve a hidden hyperlink change."""
    value = cell.value.strip()
    hyperlink = (cell.hyperlink or "").strip()
    if hyperlink and value and value != hyperlink:
        return f"{value} — {hyperlink}"
    return hyperlink or value


def _change(
    cell: CellSnapshot,
    change_type: ChangeType,
    old_value: str | None,
    new_value: str | None,
    timestamp: datetime,
    field_name: str | None = None,
    row_label: str | None = None,
) -> ChangeRecord:
    return ChangeRecord(
        id=stable_hash(cell.stable_key, change_type, old_value, new_value, timestamp.isoformat()),
        source_id=cell.source_id,
        workbook_name=cell.workbook_name,
        sheet_name=cell.sheet_name,
        coordinate=cell.coordinate,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        detected_at=timestamp,
        field_name=field_name,
        row_label=row_label,
    )
