from datetime import UTC, date, datetime

from app.api.routes import _friendly_change, _group_change_stories
from app.models import ChangeRecord, ChangeType, TestRecord
from app.services.test_series import assigned_test_sunday


def _test_record(test_date: str) -> TestRecord:
    return TestRecord(
        id=f"test-{test_date}",
        source_id="source",
        workbook_name="Test Series - 2026",
        sheet_name="PRARAMBH 2026",
        source_row=10,
        fingerprint=f"fp-{test_date}",
        test_date_status=test_date,
    )


def test_monday_through_saturday_test_dates_belong_to_same_sunday() -> None:
    sunday = date(2026, 8, 9)
    for day in range(3, 10):
        assert assigned_test_sunday(_test_record(f"2026-08-{day:02d}")) == sunday


def test_same_field_across_rows_becomes_one_bulk_story() -> None:
    stamp = datetime(2026, 8, 7, 6, 0, tzinfo=UTC)
    changes = [
        ChangeRecord(
            id=str(row),
            source_id="source",
            workbook_name="Workbook",
            sheet_name="Weekly Planner",
            coordinate=f"C{row}",
            change_type=ChangeType.UPDATED,
            old_value="Amit Sir",
            new_value="Rahul Sir",
            detected_at=stamp,
            field_name="Teacher",
        )
        for row in (50, 51, 52)
    ]

    stories = _group_change_stories(changes)
    assert len(stories) == 1
    story = stories[0]
    assert story.group_kind == "field"
    assert story.affected_rows == [50, 51, 52]
    assert story.affected_count == 3
    assert _friendly_change(story).summary == "Teacher changed in 3 rows"


def test_multiple_columns_in_one_row_remain_one_row_story() -> None:
    stamp = datetime(2026, 8, 7, 6, 0, tzinfo=UTC)
    changes = [
        ChangeRecord(
            id="time",
            source_id="source",
            workbook_name="Workbook",
            sheet_name="Weekly Planner",
            coordinate="B60",
            change_type=ChangeType.UPDATED,
            old_value="5 PM",
            new_value="6 PM",
            detected_at=stamp,
            field_name="Time",
        ),
        ChangeRecord(
            id="topic",
            source_id="source",
            workbook_name="Workbook",
            sheet_name="Weekly Planner",
            coordinate="D60",
            change_type=ChangeType.UPDATED,
            old_value="Motion",
            new_value="Laws of Motion",
            detected_at=stamp,
            field_name="Topic",
        ),
    ]

    stories = _group_change_stories(changes)
    assert len(stories) == 1
    assert stories[0].group_kind == "row"
    assert stories[0].affected_rows == [60]
    assert len(stories[0].details) == 2
