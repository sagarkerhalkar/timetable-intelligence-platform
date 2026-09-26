# 2026-09-26 — smfffdy urgent local dynamic QR fix package

## User requirement
- Fix the existing permanent QR `https://q.nexttoppers.workers.dev/q/smfffdy` urgently on the local Windows server.
- Preserve the exact QR slug/pixels; do not regenerate or reprint it.
- Allow the destination URL to change later while the same QR continues to work.
- Keep Active/Inactive separate from destination editing.
- Keep Sheets, Timetable, Test Monitor, Sheet Updates and the working web app unchanged.
- Do not touch protected port 3457.

## Root cause confirmed from source
The current local `qr-fast` resolver rejects inactive database rows with HTTP 410, but its successful resolve payload omitted the `active` field. The Cloudflare edge Worker normalizes route input with `active: Boolean(value.active)`, so a fallback route without `active` can be persisted/cached as inactive.

The existing QR management API already preserves QR identity on edit: PATCH `/api/v1/qr-codes/{qr_id}` updates the existing record/target, while POST `/api/v1/qr-codes/{qr_id}/active` controls Active/Inactive independently.

## Urgent local package
Package: `NEXTTOPPERS_QR_SMFFFDY_URGENT_FIX.zip`

SHA-256: `1327ab7649b44efdf5746dfadc63a7007cfba4898473a90af3bf8d915b28abd7`

### Package behavior
1. Verifies API 3550 is healthy.
2. Confirms slug `smfffdy` exists exactly once and is Tracked mode.
3. Confirms the existing edge-sync secret is present locally.
4. Determines which SQLite DB API 3550 is actually serving by matching source IDs, timetable total and QR slug set.
5. Verifies SQLite integrity and foreign keys.
6. Backs up current `routes.py`, `qr_fast.py`, the live DB and the other DB copy if present.
7. Patches `qr_fast.py` so successful resolve returns `active: bool(row["active"])`.
8. Adds QR-only edge synchronization after an existing QR target/experience PATCH and after an Active/Inactive change.
9. Restarts only API 3550 with the proven live DB explicitly pinned.
10. Sets only QR `smfffdy` to `active=true` through the existing API.
11. Pushes the same slug/target/active state to the existing Cloudflare Worker KV route through `/__ntqr_admin/sync`.
12. Verifies the QR ID, slug and destination stayed unchanged.
13. Verifies local `/api/v1/qr-fast/smfffdy/resolve` returns `active=true`.
14. Verifies the public `smfffdy` URL no longer reports inactive.
15. On failed acceptance after backup, restores the pre-fix QR source and live DB and restarts the previous API baseline.

## Explicitly untouched
- web port 3500
- protected development port 3457
- Google Sheets sync/parser
- Timetable
- Test Monitor
- Sheet Updates
- Cloudflare Worker deployment/bindings
- KV namespace creation/deletion
- QR slug/image/pixels
- current QR destination URL

## Local package validation before delivery
- ZIP CRC: PASS
- installer Python syntax: PASS
- patched `qr_fast.py` syntax: PASS
- patched `routes.py` syntax: PASS
- source compatibility/idempotency self-test: PASS

## Windows acceptance status
NOT YET ACCEPTED. Awaiting the user to run `RUN_QR_SMFFFDY_FIX_NOW.cmd` on the real Windows server.

Acceptance requires the package to print:
`SUCCESS - QR smfffdy IS ACTIVE AND DYNAMIC`

and the same existing public QR must scan without the inactive response.
