# v1.0.11 performance and weekly test operations

## Root cause

The Test Series workbook was expanded three times in one sync: general analysis, dedicated test parsing and generic structured-content parsing. After the first two passes, the redundant third open caused severe memory pressure and left Windows showing `analyzing` for 30 minutes.

## Performance corrections

- Skip the third generic parse when dedicated structured tests are found.
- Inspect populated/hyperlinked cells rather than every formatted blank cell.
- Run workbook parsing outside the API request loop.
- Serialize Google Sheet work through one queue.
- Keep old successful data visible until replacement succeeds.
- Repair interrupted sync states at startup.
- Delay automatic checks for two minutes and refresh only stale sources.
- Use SQL pagination for empty Search and SQL aggregation for dashboard totals.
- Queue remote Sheet refresh only after the installer has successfully validated code, tests, build, API version and web pages.

## Weekly Sunday test rules

- Upload window: Monday 9:00 AM through Saturday 6:00 PM.
- Test day: coming Sunday.
- App readiness: Saturday 6:00 PM.
- Result Dashboard deadline: Monday 6:00 PM after the Sunday test.
- Video Solution deadline: Tuesday 6:00 PM after the Sunday test.
- An explicit Test Date overrides automatic assignment.

## UI

Test Monitor displays tab totals, subject totals, exact next-Sunday tests, App readiness, result/video deadlines, file coverage and data-quality analytics. Sheet Updates defaults to an Excel-style Row / Column / Cell / Before / After table.

## Real workbook validation

- Test Series - 2026: about 5 seconds, 754 tests, 782 Search records.
- YT Science 2026-27: about 0.6 seconds, 95 Class 11 records and 77 Class 12 records.
- Commerce Classes 11 & 12: about 4.8 seconds, 59 timetable entries and 703 Search records.
- Backend: 69 tests passed.
- TypeScript/TSX: 41 source files parsed with zero syntax diagnostics.

Port 3457 remains protected. Databases, credentials, recipients, logs, runtime files and backups are excluded from the release package.
