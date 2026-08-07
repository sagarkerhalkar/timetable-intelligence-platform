# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.14.1-pagination-contract-fix.zip`

SHA-256: `9a11d8fb9fed005bd8a1c676b015a792514f8d54b2684cd4fde636fa33eecca0`

## v1.0.14.1 performance build + pagination contract repair

- Preserves the v1.0.14 maximum-performance changes: SQL-filtered timetable reads, compact cached Test Monitor responses, 5-second API/SQLite ceilings, instant loading shell, stale-safe read caching, and no forced all-Sheet refresh immediately after installation.
- Fixes the exact Windows regression from v1.0.14: `/api/v1/timetable?page=99&page_size=1` returned `200 OK` with an empty page when timetable records existed, but the long-standing API contract and backend test require HTTP 404 for an out-of-range page.
- The fast SQL path is retained. The route reuses the SQL `COUNT(*)` already returned by `list_timetable_page`; it does not reload the whole timetable in Python.
- Empty datasets still keep page 1 valid with `total=0` and `pages=1`.
- The Windows installer continues to run the complete installed backend test suite before TypeScript/build/start validation. Any failure restores the previous source, both databases and `.next` build.
- Existing databases, connected Google Sheets, notification rules and protected port 3457 remain preserved.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes databases, credentials, recipients, logs, runtime files and backups.
