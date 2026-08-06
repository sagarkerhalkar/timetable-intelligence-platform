# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.11-performance-weekly-test-ops.zip`

SHA-256: `7295c2bf67286a1550c46f21b826ac781b26975c4a0ac603f2056e8260ca8c21`

## v1.0.11 responsive background sync and weekly test operations

- Fixes the real 30-minute Test Series stall. The previous sync opened the heavily formatted workbook three times; v1.0.11 skips the redundant third generic parse after structured test records have already been extracted.
- Profiles and generic parsers scan populated/hyperlinked cells instead of expanding every formatted blank cell.
- XLSX work runs outside the FastAPI request loop and all Google Sheets use one serialized queue, keeping the local API and pages responsive.
- Old successful timetable, Search and Test data remain visible until a complete replacement dataset is ready. Interrupted sync states are repaired at startup.
- Automatic checks begin after a two-minute startup delay and refresh only stale sources. Empty Search and dashboard totals use SQL-backed queries.
- The Windows installer validates code, 69 backend tests, TypeScript and the full Next.js build, checks the new pages, then queues Google Sheets in the background. It does not wait 30 minutes or roll back because a remote Sheet is slow.
- Weekly Test Monitor rule: Monday 9:00 AM through Saturday 6:00 PM uploads go to the coming Sunday; App readiness is Saturday 6:00 PM; Result Dashboard is Monday 6:00 PM; Video Solution is Tuesday 6:00 PM.
- Clicking a Test Series tab shows total tests by subject and the exact next-Sunday subject/test counts.
- Sheet Updates defaults to an Excel-style audit table with Sheet, tab, row, column, cell, field, change, before and after.
- Real local parser benchmarks: Test Series about 5 seconds (754 tests, 782 Search records), YT Science about 0.6 seconds (Class 11 = 95, Class 12 = 77), Commerce about 4.8 seconds (59 timetable entries, 703 Search records).
- Existing database, connected Google Sheets, notification rules and isolated ports remain preserved. Port 3457 remains protected.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes databases, credentials, recipients, logs, runtime files and backups.
