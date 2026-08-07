# v1.0.14 performance cache and instant navigation

## Problem reproduced

The Aug 7 screen recording shows Test Monitor and normal page navigation taking far too long. Several waits match the previous 15-second API timeout window. v1.0.13 also forced all connected Google Sheets to refresh immediately after restart, so Test Series, Science, Commerce, Humanities and Nirmaan parsing could compete with interactive page requests.

## Corrections

- Normal read APIs use short Next.js revalidation instead of `cache: no-store` on every navigation.
- Today/Weekly/stream timetable filtering moved from “load every timetable row + Python filter” to SQL date/stream/class/subject filtering and SQL pagination.
- Added timetable date/date+time expression indexes.
- SQLite interactive lock wait is capped at 5 seconds instead of 30 seconds, with a 32 MB connection cache and in-memory temporary tables.
- Default server-side API timeout is reduced from 15 seconds to 5 seconds.
- A global `loading.tsx` shell makes route transitions visible immediately.
- Test Monitor uses compact responses for the normal page and a 45-second in-process cache by source/tab/compact mode.
- Lightweight Test tab counts schedule one sequential warm pass so first clicks can hit warm summaries without parallel CPU spikes.
- Test Monitor no longer loads Sources / notification setup on the main readiness page.
- Test page auto-refresh is 5 minutes instead of 2 minutes.
- The Windows installer no longer forces an all-Sheet refresh after every update. The normal 30-minute scheduler owns Sheet freshness.
- The installer warms read-only dashboard/Test/Today/Weekly/Sheet Updates paths before opening the browser.

## Preserved behavior

- v1.0.13 one-click Today stream navigation and Test tab state.
- v1.0.12 human-readable Sheet Updates, same-row/same-field grouping and clickable changed links.
- Monday-Saturday Sheet Test Date -> same-week Sunday logic.
- v1.0.11.1 strict TypeScript `cellParts()` fix.
- Existing databases, Sheet connections, notification rules, LAN ports and protected development port 3457.
