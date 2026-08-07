# Timetable Intelligence v1.0.13 validation

## User-reported failures addressed

- Today stream cards for Commerce, Science, Humanities and Nirmaan were plain display elements and could not open a stream-wise timetable.
- Test Monitor source tabs could appear to ignore the first click and could take too long because a selected-tab page performed two monitor analytics calls and the backend loaded every test record before filtering the requested tab in Python.

## Corrections validated

- Today stream controls are direct links carrying the current date and exact stream filter.
- The whole stream card is clickable and keyboard focusable with visible hover/focus feedback.
- Test Monitor clicked tab becomes active immediately, confirms the click was accepted, and blocks duplicate clicks on the already-pending tab.
- Test Monitor server rendering performs one monitor request for the selected tab instead of an all-data request plus a second selected-tab request.
- New `/api/v1/test-monitor/tabs` returns tab totals through a small SQLite `GROUP BY` query.
- Selected tabs use indexed `test_records(source_id, sheet_name)` filtering instead of loading all tabs and filtering afterward.

## Local validation

- SQLite fast tab totals regression: passed.
- SQLite selected-tab filtering regression: passed.
- Changed Python files compile: passed.
- Changed TypeScript/TSX files: zero syntax diagnostics.
- Strict TSX check with `strict` and `noUncheckedIndexedAccess`: passed for Today, Test Monitor and tab switching with local framework declaration stubs.
- Strict `api.ts` + `types.ts` check: passed.
- v1.0.11.1 `cellParts()` safety checks remain present.
- PowerShell structural/interpolation check: passed.
- ZIP integrity: passed.

## Windows acceptance boundary

The installer performs the authoritative full backend test suite, real `npm run typecheck`, complete Next.js production build, API version check, Today stream page checks, lightweight Test tab endpoint check, filtered Test-tab timing checks and Sheet Update response checks on the installed Windows dependency tree. Any failure restores the previous changed files, both database locations and `.next` build.

Protected development port 3457 is not modified.
