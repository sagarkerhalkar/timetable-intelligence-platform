# v1.0.25.4 - Full App Web/API Bridge Recovery

This recovery exists for the 2026-08-13 incident where the authoritative FastAPI service/database was healthy but the Next.js UI showed empty timetable/Google Sheet states and HTTP 404 because the browser-facing `/backend` bridge was absent/unreliable.

## Product source change
`apps/web/app/backend/[...path]/route.ts` is the only application-source change. It proxies same-origin browser requests from `/backend/*` to `http://127.0.0.1:3550/*` and supports GET/POST/PUT/PATCH/DELETE/OPTIONS, query strings, JSON and binary QR responses.

## Required web environment
Create/preserve `apps/web/.env.local` and ensure these two keys exist exactly once:

```text
INTERNAL_API_URL=http://127.0.0.1:3550
NEXT_PUBLIC_API_URL=/backend
```

Other existing environment keys must be preserved.

## Recovery procedure
1. Read-only verify `services/api/data/timetable.db` integrity and counts before touching web.
2. Directly verify API 3550: dashboard, sources, Today timetable, tests/changes and QR.
3. Back up existing proxy file, `apps/web/.env.local`, and `.next`.
4. Install the route above and the two web environment keys.
5. Stop only Node listener on 3500. Never touch 3457 and do not stop API 3550.
6. Run `npm run typecheck` from `apps/web`.
7. Run `npm run build` from `apps/web` with the two environment values above.
8. Start Next directly on `0.0.0.0:3500` using the local Next binary. If Windows refuses production start, current-source `next dev -H 0.0.0.0 -p 3500` is an allowed temporary runtime fallback; do not change DB/API to compensate for a web-start problem.
9. Acceptance MUST call the same browser route used by the UI, e.g. `http://127.0.0.1:3500/backend/api/v1/dashboard`, not only direct port 3550.
10. Require browser-bridge sources >= 4, Today 2026-08-13 timetable rows > 0, QR rows >= 24, and HTTP 2xx for Today/Week/Sources/Content/Changes/Tests/My QR Codes.

## Data safety baseline for this incident
Before this fix Windows evidence showed:
- sources=4
- timetable_entries=989
- test_records=1122
- changes=95
- qr_codes=24
- qr_scans=24
- Today 2026-08-13 rows after successful Sheet sync=12

This recovery must not modify those SQLite records.

## Distributed package
`FULL_TIMETABLE_INTELLIGENCE_RUNNING_FIX_V1_0_25_4.zip`

SHA-256:
`86586eabb962786bedd97d8f1006efb614352ebdd6d7a6634a9ae699262ba4b8`

The user package also contains the Windows orchestration script and read-only verifier implementing the procedure above.

## Acceptance marker
Do not claim success until Windows prints:

`SUCCESS - FULL APP DATA PATH IS WORKING`

Stable `v1` remains untouched until full Windows acceptance succeeds.
