from __future__ import annotations

from datetime import UTC, datetime

from app.models import CellSnapshot, ChangeType
from app.services.change_detector import detect_cell_changes


def cell(coordinate: str, value: str) -> CellSnapshot:
    row = int("".join(character for character in coordinate if character.isdigit()))
    return CellSnapshot(
        source_id="source",
        workbook_name="book",
        sheet_name="tab",
        coordinate=coordinate,
        row=row,
        column=1,
        value=value,
    )


def test_detect_added_updated_and_deleted_cells() -> None:
    previous = [cell("A1", "old"), cell("A2", "deleted")]
    current = [cell("A1", "new"), cell("A3", "added")]
    changes = detect_cell_changes(previous, current, datetime(2026, 8, 4, tzinfo=UTC))
    assert {item.change_type for item in changes} == {
        ChangeType.ADDED,
        ChangeType.UPDATED,
        ChangeType.DELETED,
    }
    updated = next(item for item in changes if item.change_type == ChangeType.UPDATED)
    assert updated.old_value == "old"
    assert updated.new_value == "new"


def test_hyperlink_change_is_visible_in_daily_history() -> None:
    before = cell("A1", "Video lesson").model_copy(update={"hyperlink": "https://example.com/old.mp4"})
    after = cell("A1", "Video lesson").model_copy(update={"hyperlink": "https://example.com/new.mp4"})
    changes = detect_cell_changes([before], [after])
    assert len(changes) == 1
    assert "old.mp4" in (changes[0].old_value or "")
    assert "new.mp4" in (changes[0].new_value or "")
