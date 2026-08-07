# v1.0.14 application patch map

This public patch map records the runtime changes without committing databases, credentials, recipients, Google Sheet data, logs or backups.

## `apps/web/lib/api.ts`

- `getJson()` now accepts `{ revalidate, timeoutMs }`.
- Read-only calls use short Next.js revalidation.
- Default timeout changes from 15000 ms to 5000 ms.
- Dashboard/Sources use 4-5 second ceilings.
- Notification administration remains `no-store`.
- `getTestMonitor(..., compact=true)` requests compact Test responses.

## `apps/web/app/loading.tsx`

Adds a global route loading boundary so navigation visually changes immediately while server data is resolving.

## `apps/web/app/tests/page.tsx`

- Removes `getSources()` from the readiness critical path.
- Notification setup is kept on the Notifications page.
- Requests compact Test Monitor data.
- Auto-refresh returns to 5 minutes.
- Pending counts use summary counters rather than relying on truncated detail arrays.

## `apps/web/components/test-tab-switcher.tsx`

Preserves first-click pending state and adds route prefetch on hover/focus.

## `services/api/app/api/routes.py`

- Adds 45-second Test Monitor response cache keyed by source/tab/compact mode.
- Lightweight `/test-monitor/tabs` schedules one sequential background warm pass.
- Compact mode keeps Sunday records but caps collapsed pending-detail arrays and omits unused recent-test records.
- `/timetable` now calls SQL-filtered `Database.list_timetable_page()` instead of loading the complete timetable and filtering in Python.

## `services/api/app/database.py`

- Adds timetable class-date and class-date/start-time expression indexes.
- Adds SQL timetable filtering, ordering and pagination for exact date, date ranges, stream, class, subject, latest and upcoming views.
- SQLite connection wait ceiling changes from 30 seconds to 5 seconds.
- Adds in-memory temporary tables and a 32 MB SQLite connection cache.

## Windows installer

- Does not force an all-Sheet refresh after restart.
- Normal 30-minute scheduler retains refresh ownership.
- Warms read-only Dashboard/Test/Today/Weekly/Sheet Updates paths before opening the browser.
- Validates cached Test-tab second-hit timing and keeps rollback protection.

## Performance validation

Synthetic 12,000-row timetable benchmark in the build environment:

- old full-table deserialization: 152.8 ms
- new SQL-filtered request: 4.6 ms
- observed speedup for that operation: about 33.6x

The real Windows machine remains the authoritative end-to-end performance environment.
