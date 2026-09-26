# 2026-09-26 - QR inactive + same QR / changeable destination

## User report
- Existing printed QR is showing **inactive**.
- Requirement: **keep the exact same QR / slug / printed pixels, but allow the destination link to change**.
- User supplied Drive folder: `1JCqoUkoQpuZcgBuxqRwkjbxbf2hm4BgR`.

## Evidence reviewed
### Drive recovery folder
`README_FIRST.txt` in the supplied folder records that the rebooted/running API on port 3550 was serving the older root QR dataset from:
`D:\timetable-intelligence-platform\data\timetable.db`
with 24 QR codes, while the newer QR dataset was in:
`D:\timetable-intelligence-platform\services\api\data\timetable.db`
with 23 newer QR codes.

This is the known QR database split. A QR may therefore resolve against an older record/state than the operator expects.

### API behavior
Current QR resolve code checks the existing QR row by slug and returns HTTP 410 when `active` is false. Destination URL is stored separately as `target_url`.

### Worker / edge behavior
The edge-KV Worker stores a route object containing `slug`, `target_url`, and `active`. If an existing KV route says `active=false`, the Worker returns the inactive page before redirecting. Therefore an out-of-date KV copy can keep a QR inactive even after local DB state is changed unless the route is synchronized.

## Root cause classification
**Confirmed design failure mode:** inactive is data/state driven, not a damaged QR image.

There are two state layers that can independently cause the inactive result:
1. the authoritative SQLite QR row has `active=0`; or
2. the Cloudflare edge/KV copy for the same slug is stale with `active=false`.

The historical DB split increases the chance that the operator edits one database while the running API/edge route is using another.

## Required permanent behavior
For tracked/dynamic QR codes:
- `slug` is immutable after creation.
- encoded QR URL / printed pixels remain unchanged.
- changing destination updates only `target_url` (plus normal updated timestamp).
- active/inactive is explicit and independent of destination changes.
- every target or active-state change must synchronize the same slug to the edge route store.
- edge update failure must be visible in admin UI/logs; it must not silently leave a stale route.
- deleting or changing a destination must never generate a new slug unless the user explicitly creates a new QR.

## Repair direction
1. Determine the slug shown by the failing QR.
2. Read that slug from the DB currently served by API 3550 and from the service/API DB.
3. Preserve `id` + `slug`; do not regenerate QR image.
4. Set the intended `active` state and update `target_url` on the authoritative record only after a backup.
5. Push the same route (`slug`, `target_url`, `active`, experience metadata) to Cloudflare edge/KV.
6. Verify public `https://q.nexttoppers.workers.dev/q/<slug>` no longer returns the inactive response and redirects to the intended destination.
7. Keep stable `v1` and protected port 3457 untouched.

## Important
Do not run a whole-database replacement or a blind v1.0.29.x deployment merely to repair one QR. The correct repair is **slug-preserving QR-state reconciliation** between the actually served DB and the edge route.
