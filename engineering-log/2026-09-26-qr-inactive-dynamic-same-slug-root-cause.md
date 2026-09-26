# QR inactive incident + same-QR dynamic destination requirement — 2026-09-26

## User-visible failure
Existing NextToppers QR codes scan to an **inactive** response. The user requires the **same printed QR image / same slug** to remain valid while the destination link may be changed later.

## Current source reviewed
The current Google Drive project source was inspected, including `services/api/app/api/routes.py`, `services/api/app/api/qr_fast.py`, `services/api/app/config.py`, and `services/api/app/main.py`.

## Confirmed code behavior
1. Tracked QR images encode the stable public route `public_base_url + /q/ + slug`; they do not encode the destination URL directly.
2. Editing a URL QR updates `target_url`/content and does not change the slug.
3. Activation is a separate state. The API returns HTTP 410 when `active` is false.
4. Current local `qr_fast.py` is the older 8,507-byte `edge-resolve` implementation. Its resolve response checks `row["active"]`, but when active it returns route JSON **without an `active` field**.
5. The deployed/historical Edge-KV Worker contract normalizes route input with `active: Boolean(value.active)` and returns 410 when the normalized edge route is inactive.

## Root cause
There is a contract mismatch between the current local fast resolver and the Edge-KV Worker:

- Local `/api/v1/qr-fast/{slug}/resolve` omits `active` after validating it.
- The Worker interprets a missing `active` value as `false`.
- Therefore an edge fallback/cache refresh can turn a valid local QR into an edge route marked inactive.

There is a second persistence problem: the current local 8,507-byte `qr_fast.py` has no Worker/KV reconciliation loop. Even after a target URL or active state changes in the local app, a previously cached Edge-KV route can remain stale.

## Locked product contract
For tracked/dynamic QR codes:

- Never change the existing slug to edit a destination.
- Never regenerate the QR merely because the destination link changes.
- Preserve the stable encoded URL and QR pixels.
- Update only `target_url` / URL content.
- Synchronize `target_url`, `active`, experience metadata and `updated_at` to the edge route store.
- Direct QR mode cannot support destination changes without changing pixels; this requirement applies to tracked QR mode.

## Safe repair design
QR-only repair; do not change timetable, Google Sheet parsing, Test Monitor, Sheet Updates, web build, or protected port 3457.

1. Back up the current QR fast source and active SQLite DB.
2. Replace only `services/api/app/api/qr_fast.py` with a contract-compatible version that:
   - includes `active` in route JSON;
   - retains the existing resolve/confirm behavior;
   - performs isolated Edge-KV reconciliation in a daemon thread every 5 seconds;
   - exposes read-only edge-sync status;
   - does not make edge-sync health a dependency of the timetable API health endpoint.
3. Restart only API 3550 using an absolute verified DB path.
4. Use the existing activation API for the selected QR if it is inactive.
5. Push/reconcile the selected route to the Worker using the existing local edge-sync secret; do not deploy/replace the Worker.
6. Verify local resolve, edge sync, public QR response and QR PNG SHA-256 before/after.
7. Acceptance requires the slug and QR image hash to remain unchanged.

## GitHub policy
This repair is **not promoted to a clean working/production branch until real Windows acceptance passes**. This engineering record is on the existing QR engineering branch so a failed candidate cannot be mistaken for accepted working code.
