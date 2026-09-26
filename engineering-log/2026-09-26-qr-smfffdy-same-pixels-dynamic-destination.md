# 2026-09-26 - QR `smfffdy`: preserve QR pixels, allow destination changes

## User-reported failing public QR
`https://q.nexttoppers.workers.dev/q/smfffdy`

The user reports the public QR currently shows **inactive**.

## Locked product requirement
- Existing printed QR must remain exactly the same.
- The permanent slug `smfffdy` must not be regenerated or replaced.
- QR image/pixels must not change merely because the destination changes.
- Destination URL may be changed at any time.
- Activation/deactivation is a separate control from destination editing.
- A destination or active-state change must update the public edge route for the same slug.
- Scan path remains `QR -> q.nexttoppers.workers.dev/q/smfffdy -> current destination`.
- QR redirect performance target remains <= 0.6 s redirect overhead after the route is present at the edge.

## Current code evidence
- QR image generation for tracked codes encodes the tracking URL containing the stable slug, not the final destination.
- PATCH `/api/v1/qr-codes/{qr_id}` updates `target_url` on an existing QR record without allocating a new slug.
- POST `/api/v1/qr-codes/{qr_id}/active?active=true|false` changes only the active state.
- QR fast resolver returns HTTP 410 when the stored route has `active=false`.
- Edge Worker/KV also stores an `active` field, so local SQLite and edge KV must be kept consistent.

## Likely current failure class
For `smfffdy`, the inactive page means the route currently being served has `active=false` somewhere in the authoritative route path. Because this project previously had a root/service SQLite split plus Worker/KV persistence across rollback, the exact authoritative local record and edge record must be reconciled for this slug without regenerating it.

## Correct repair design
1. Locate `smfffdy` in the running API and both known SQLite copies.
2. Preserve its `id`, `slug`, design, tracking URL and QR pixels.
3. Set the authoritative local record active when required.
4. Push the same slug's current `target_url` + `active` state to Cloudflare edge/KV immediately.
5. Verify local resolve and public Worker resolve for the same slug.
6. For future QR edits, make target/active mutations event-driven to edge sync so no stale KV route can remain.
7. Do not touch timetable, tests, sheets, web 3500, or protected 3457 for this repair.
