# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.13-fast-navigation.zip`

SHA-256: `fdbb8b647c4e238be4c0238959cdf5cf9bc972e9976359f9ed2d670bac30fcbe`

## v1.0.13 fast navigation and one-click Test Monitor

- Today now makes Commerce, Science, Humanities and Nirmaan real clickable cards. One click opens the exact current-day stream timetable using date + stream filters.
- Test Monitor now gives immediate visual feedback on the first click. The clicked PRARAMBH/Nirman/other tab becomes active at once and duplicate clicks on the already-pending tab are ignored.
- A selected Test Monitor tab now performs one analytics request instead of first loading all tests and then loading the selected tab again.
- Selected test tabs are filtered directly in SQLite with the existing `test_records(source_id, sheet_name)` index instead of loading all test records and filtering them in Python.
- New lightweight `/api/v1/test-monitor/tabs` uses SQL `GROUP BY` counts so the navigation bar no longer requires a full analytics payload.
- v1.0.12 human-readable Sheet Updates, grouped same-row/same-field changes, directly clickable changed links and Monday-Saturday-to-Sunday test-cycle logic are preserved.
- v1.0.11.1 strict TypeScript `cellParts()` protection remains in place; strict and `noUncheckedIndexedAccess` stay enabled.

## Validation

- Local SQLite fast-tab aggregation and selected-tab filtering regressions passed.
- Changed Python files compile successfully.
- Changed TypeScript/TSX files transpile with zero syntax diagnostics.
- Strict TSX checks with `strict` + `noUncheckedIndexedAccess` passed for Today, Test Monitor and the tab switcher using local framework declaration stubs.
- Strict `api.ts` + `types.ts` check passed.
- PowerShell structure/interpolation validation passed.
- ZIP integrity passed.
- The Windows installer still runs the complete backend tests, real `npm run typecheck`, complete Next.js production build, API version check, Today stream page checks and filtered Test-tab timing checks before accepting the update. Any failure restores the previous files, both database locations and `.next` build.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes databases, credentials, recipients, logs, runtime files and backups. Protected development port 3457 is not changed.
