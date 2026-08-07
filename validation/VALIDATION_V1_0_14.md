# Timetable Intelligence v1.0.14 validation

## User-reported failure

Screen recording dated 2026-08-07 shows Test Monitor remaining too slow after v1.0.13 and overall application navigation taking too long.

## Root causes addressed

1. Read-only Next.js API calls were explicitly `no-store` and allowed to block each navigation for up to 15 seconds.
2. Test Monitor returned large collapsed-detail arrays not required for the first screen.
3. Timetable routes loaded and deserialized the entire timetable table before applying date/stream filters in Python.
4. SQLite connections allowed up to 30 seconds of lock waiting.
5. v1.0.13 immediately queued all connected Google Sheets after restart, creating workbook parsing pressure while the user opened the app.
6. Route changes had no global loading boundary.

## Build-environment checks

- Modified Python files compile successfully.
- SQL timetable regression passed for exact date + stream, date range and latest-date filtering.
- Synthetic 12,000-row benchmark: 152.8 ms old full-table path vs 4.6 ms SQL-filtered path, about 33.6x faster for that operation in this environment.
- Changed TS/TSX files transpile without syntax diagnostics.
- Strict Test Monitor/loading-shell TSX check passed with `strict` and `noUncheckedIndexedAccess`.
- Strict `api.ts` + `types.ts` check passed.
- Source regression assertions confirm 5-second API ceiling, revalidation cache, compact Test request, 45-second Test cache, global loading boundary and no forced post-install Sheet refresh.
- PowerShell delimiter/quote structural check passed.
- Installer payload path completeness passed.
- ZIP integrity passed.

## Windows authoritative boundary

The user's installed dependency tree and real database exist only on the Windows server. The installer therefore keeps rollback protection and runs the complete installed Python test suite, real `npm run typecheck`, complete Next.js production build, health/page checks and cached Test-tab timing checks before accepting v1.0.14. Failure restores the prior files, both database locations and `.next` build.
