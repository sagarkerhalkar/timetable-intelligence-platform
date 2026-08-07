# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.14-performance-cache.zip`

SHA-256: `53479fa5ac6e738c029a69b9f071c5d465fd76dbd987ba3b3399f466ced8ac64`

## v1.0.14 maximum-performance update

- Reproduced from the Aug 7 screen recording: Test Monitor and normal page changes were still too slow after v1.0.13.
- Read-only Next.js API calls now use short stale-safe revalidation instead of forcing `cache: no-store` on every navigation.
- Default server-side API wait ceiling is reduced from 15 seconds to 5 seconds; dashboard/source reads use 4-5 second ceilings.
- A global `loading.tsx` boundary gives immediate route-change feedback instead of leaving the previous page looking frozen.
- Test Monitor normal responses are compact and cached in-process for 45 seconds by source/tab. Lightweight tab counts schedule one sequential warm pass so first tab clicks can use warmed results.
- Test Monitor no longer fetches Sources / notification setup just to render the readiness page; notification setup stays on the Notifications page.
- Today / Weekly / stream timetable filtering moved from full-table Python deserialization to SQL date/stream/class/subject filtering and SQL pagination, with timetable date indexes.
- SQLite interactive lock wait is capped at 5 seconds instead of 30 seconds, with a 32 MB connection cache and in-memory temporary tables.
- The installer no longer forces Science + Commerce + Humanities + Nirmaan + Test Series to refresh immediately after restart. The normal 30-minute scheduler refreshes them later, so workbook parsing does not compete with the user's first clicks.
- The installer warms read-only Dashboard, Test, Today, Weekly and Sheet Updates paths before opening the browser.
- v1.0.13 one-click Today/Test navigation, v1.0.12 human-readable Sheet Updates/clickable links, Monday-Saturday -> same-week Sunday logic and the v1.0.11.1 strict TypeScript fix are preserved.

## Validation

- Python application compilation passed.
- SQL timetable regression passed for exact date + stream, date range and latest-date filtering.
- Synthetic 12,000-row benchmark: old full-table timetable deserialization 152.8 ms vs SQL-filtered request 4.6 ms, about 33.6x faster in this build environment.
- Strict Test Monitor/loading-shell TypeScript checks passed with `strict` + `noUncheckedIndexedAccess`.
- Strict `api.ts` + `types.ts` check passed.
- PowerShell structure and installer payload-path checks passed.
- No forced post-install all-Sheet queue call remains.
- ZIP integrity passed.
- The Windows installer remains authoritative: it runs the complete installed backend tests, real `npm run typecheck`, full Next.js production build, health/page checks and cached Test-tab timing checks before accepting the update. Failure restores the previous files, both database locations and `.next` build.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes databases, credentials, recipients, logs, runtime files and backups. Protected development port 3457 is not changed.
