from __future__ import annotations

import asyncio
import gc
from datetime import UTC, datetime
from pathlib import Path

from ..config import Settings
from ..database import Database
from ..models import SheetSource, SyncResult
from .change_detector import detect_cell_changes
from .google_sheets import download_public_workbook
from .sheet_schema import parse_structured_content_workbook
from .test_series import parse_test_workbook
from .workbook_analyzer import WorkbookAnalyzer


class SyncService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings
        self.analyzer = WorkbookAnalyzer()
        # XLSX parsing is memory-heavy. Running two Google Sheet checks at the
        # same time caused Windows to page heavily, the API health request to
        # time out, and Test Series to remain "analyzing" for 30 minutes. One
        # process-wide queue keeps the web/API responsive and still refreshes
        # every source in order.
        self._sync_lock = asyncio.Lock()

    async def sync_source(self, source: SheetSource) -> SyncResult:
        started = datetime.now(UTC)
        path: Path | None = None
        try:
            # Routes set queued before scheduling. Automatic refresh calls this
            # directly, so make the waiting state explicit there as well.
            self.database.update_source_sync_status(source.id, "queued")
            async with self._sync_lock:
                current = self.database.get_source(source.id)
                if current is None:
                    completed = datetime.now(UTC)
                    return SyncResult(
                        source_id=source.id,
                        status="removed",
                        started_at=started,
                        completed_at=completed,
                        live_data=False,
                        warnings=["The local Google Sheet connection was removed before checking started."],
                    )
                if not current.enabled:
                    completed = datetime.now(UTC)
                    self.database.update_source_sync_status(current.id, "disabled", None, completed)
                    return SyncResult(
                        source_id=current.id,
                        status="disabled",
                        started_at=started,
                        completed_at=completed,
                        live_data=False,
                    )

                self.database.update_source_sync_status(current.id, "downloading")
                path = await download_public_workbook(
                    current.spreadsheet_id,
                    max_download_mb=self.settings.max_download_mb,
                    timeout_seconds=self.settings.sync_timeout_seconds,
                )
                self.database.update_source_sync_status(current.id, "analyzing")
                # CPU and XLSX work stays outside the ASGI loop. The global lock
                # above prevents concurrent workbook expansion and memory thrash.
                result = await asyncio.to_thread(
                    self.sync_local_workbook,
                    current,
                    path,
                    live_data=True,
                    started_at=started,
                )
                if result.new_test_ids:
                    from .notifications import dispatch_new_test_notifications
                    await dispatch_new_test_notifications(
                        self.database,
                        self.database.get_test_records(result.new_test_ids),
                    )
                return result
        except Exception as exc:
            completed = datetime.now(UTC)
            message = str(exc)
            self.database.update_source_sync_status(source.id, "error", message, completed)
            self.database.record_sync(source.id, "error", False, started, completed, 0, message)
            return SyncResult(
                source_id=source.id,
                status="error",
                started_at=started,
                completed_at=completed,
                live_data=False,
                error=message,
                warnings=["Old local data was kept. This failed check did not replace it."],
            )
        finally:
            if path and path.exists():
                path.unlink(missing_ok=True)
            gc.collect()

    def sync_local_workbook(
        self,
        source: SheetSource,
        workbook_path: Path,
        *,
        live_data: bool,
        started_at: datetime | None = None,
    ) -> SyncResult:
        started = started_at or datetime.now(UTC)
        previous = self.database.get_cells(source.id)

        profile, cells, timetable, content = self.analyzer.analyze(
            workbook_path,
            source.id,
            source.name,
            spreadsheet_id=source.spreadsheet_id,
        )
        gc.collect()

        test_records, test_content = parse_test_workbook(
            workbook_path,
            source_id=source.id,
            workbook_name=source.name,
        )
        gc.collect()

        # Test Series already has a dedicated parser that understands Course,
        # Class, Subject, Chapter, status, date, result and video columns. Opening
        # the same heavily formatted workbook a third time for generic parsing
        # caused the 30-minute stall. For non-test workbooks, keep the universal
        # structured parser so custom headings such as Remarks still work.
        structured_content = []
        if not test_records:
            structured_content = parse_structured_content_workbook(
                workbook_path,
                source_id=source.id,
                workbook_name=source.name,
            )
            gc.collect()

        # Keep the specialised/high-information record when exact occurrences
        # overlap. A physical link under a custom heading is still preserved.
        merged = {
            (item.sheet_name, item.coordinate, item.url or item.title): item
            for item in content
        }
        for item in structured_content:
            merged[(item.sheet_name, item.coordinate, item.url or item.title)] = item
        for item in test_content:
            merged[(item.sheet_name, item.coordinate, item.url or item.title)] = item
        content = sorted(
            merged.values(),
            key=lambda item: (item.sheet_name, item.source_row, item.title),
        )

        # The first successful check creates a baseline. Subsequent checks keep
        # exact cell-level Add / Change / Remove history.
        changes = detect_cell_changes(previous, cells) if previous else []

        # Derived data is replaced only after all parsing succeeds, so users keep
        # seeing the previous good timetable/search data during a check.
        self.database.replace_cells(source.id, cells)
        self.database.replace_timetable(source.id, timetable)
        self.database.replace_content(source.id, content)
        new_tests = self.database.replace_test_records(source.id, test_records)
        self.database.upsert_workbook_profile(profile)
        self.database.insert_changes(changes)

        completed = datetime.now(UTC)
        status = "success" if live_data else "local_import"
        self.database.update_source_sync_status(source.id, status, None, completed)
        self.database.record_sync(
            source.id,
            status,
            live_data,
            started,
            completed,
            len(profile.warnings),
            None,
        )
        return SyncResult(
            source_id=source.id,
            status=status,
            started_at=started,
            completed_at=completed,
            live_data=live_data,
            workbook_profile=profile,
            timetable_count=len(timetable),
            content_count=len(content),
            change_count=len(changes),
            warnings=profile.warnings,
            test_record_count=len(test_records),
            new_test_ids=[item.id for item in new_tests],
        )
