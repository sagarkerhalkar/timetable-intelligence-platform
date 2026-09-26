# 2026-09-26 — QR permanent dynamic auto-sync V7

## User requirement
- Any newly generated **Tracked** QR must work without manual Cloudflare repair.
- Editing the destination of an existing Tracked QR must keep the **same QR image / same slug** and automatically update the Cloudflare edge route.
- Active/Inactive changes must stay synchronized.
- User must not need one-off helper ZIPs for every QR/link change.

## Current affected QR
- Permanent QR: `https://q.nexttoppers.workers.dev/q/5wqrrpw`
- Old destination observed on scan: `https://www.youtube.com/watch?v=TmrkmcY9flc`
- Required destination: `https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`

## V6 real Windows result
V6 confirmed the local root DB already contained the new target and successfully wrote/read back `qr:5wqrrpw` in namespace `0a1c82f1062b403cab2a74e828d7e344`.

V6 then failed on namespace `5936d23cdbf24c0890effd4c41e10c19` with Cloudflare error `namespace not found` (10013). The cause was V6 recursively collecting historical Worker version IDs instead of limiting discovery to the **currently serving production deployment**. This made stale/deleted historical QR_EDGE namespace IDs look active.

V6 rollback also hit a Windows SQLite WAL lock because the database was in use. Future rollback must stop API before restoring DB files.

## Permanent V7 design
V7 changes the application QR CRUD flow, not one slug:
- `POST /qr-codes`: create locally, then sync current production Cloudflare KV; rollback creation if edge sync fails.
- `PATCH /qr-codes/{id}`: update locally, sync same slug to edge, rollback edit if edge sync fails.
- `POST /qr-codes/{id}/active`: synchronize Active/Inactive and rollback on edge failure.
- `DELETE /qr-codes/{id}`: mark edge route inactive before local deletion.
- Bulk tracked creation: sync every created QR and rollback local batch on edge failure.
- `qr-fast` successful resolve includes explicit `active` state.

Cloudflare namespace discovery now uses only `wrangler deployments status --name q --json`, then reads those currently serving version(s), extracts their `QR_EDGE` binding IDs, and intersects them with KV namespaces that still exist. Historical deployment/version lists are intentionally not used.

The runtime helper caches valid namespace IDs for 10 minutes and force-refreshes discovery on sync failure. No Worker code, Worker secret, or Worker deployment is modified.

## V7 acceptance test
The installer must not claim success on syntax alone. After source installation and API restart it will:
1. force `5wqrrpw` through the normal patched Edit API and verify the public QR exposes `Wcb3ZPnZ5Rk`;
2. create a temporary NEW tracked QR through the normal API and verify it reaches Cloudflare;
3. edit that same temporary QR to a second URL and verify the same slug exposes the new URL;
4. verify Active/Inactive synchronization;
5. verify delete/deactivation path and remove the temporary QR.

Only then may it print `SUCCESS - PERMANENT DYNAMIC QR AUTO-SYNC IS WORKING`.

## Safety scope
- Restart API 3550 only.
- Do not touch web 3500.
- Do not touch protected dev port 3457.
- Do not modify Sheets, Timetable parser/data logic, Test Monitor, Worker code, Worker secret, or Worker deployment/version.
- Back up `routes.py`, `qr_fast.py`, current helper if present, root DB, and service DB before change.
- On failure: stop API first, restore source + DB backups, restart previous API baseline.

## Package
- `NEXTTOPPERS_QR_PERMANENT_DYNAMIC_AUTO_SYNC_V7.zip`
- SHA-256: `884f92e56e5103f5f41cc97d5e2e94caec583ad419d10ba23a043d8a64e025fe`
- Local package validation: ZIP CRC PASS; installer self-test PASS; patched routes/qr-fast/helper syntax PASS; generic create/edit/active/delete/bulk hooks PASS.

## Status
**Windows production acceptance pending.** Do not promote V7 source into the working-code branch until the real server run passes the full acceptance test above.
