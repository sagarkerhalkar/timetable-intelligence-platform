# QR smfffdy urgent V2 secret recovery

Date: 2026-09-26
Branch: `nexttoppersqr`

## User-visible failure
The first urgent QR-only installer stopped safely before changing local source or database because this file was missing/invalid:

`D:\timetable-intelligence-platform\services\api\data\qr_edge_sync_secret.txt`

Observed installer result:

`NOT ACCEPTED - QR FIX ROLLED BACK`

`Reason: Edge sync secret missing/invalid ... Nothing changed.`

## Root cause
The current Cloudflare edge Worker admin sync requires `NEXTTOPPERS_EDGE_SYNC_SECRET`, while the local API-side copy used to authenticate `/__ntqr_admin/sync` was absent. A secret value cannot be recovered from Cloudflare after deployment, so the safe correction is to rotate to a new generated secret and install the same value in both places.

The QR code itself is not regenerated. Permanent tracked slug remains:

`https://q.nexttoppers.workers.dev/q/smfffdy`

## V2 correction
Package: `NEXTTOPPERS_QR_SMFFFDY_URGENT_FIX_V2.zip`

SHA-256: `fc89ade5079f616e6aa204c371688a736a75ef1fc67fe84cc73f8d35a5533c7d`

V2 behavior:
- prechecks API 3550 and confirms `smfffdy` exists exactly once;
- preserves QR ID, slug and current target URL;
- identifies the SQLite database actually served by API 3550;
- backs up QR source and live DB before local changes;
- verifies Wrangler authentication (and opens login if required);
- generates a new strong sync secret;
- runs Wrangler `secret put NEXTTOPPERS_EDGE_SYNC_SECRET --name q`;
- writes the same secret to `services/api/data/qr_edge_sync_secret.txt`;
- proves `/__ntqr_admin/sync` accepts the new secret before source changes;
- fixes `qr-fast` resolve payload to include explicit `active`;
- adds per-edit edge synchronization after QR destination edits and Active/Inactive changes;
- restarts only API 3550 with the identified live DB pinned explicitly;
- sets `smfffdy` active=true without changing slug or target;
- writes the same route to Cloudflare edge and waits for stale KV cache propagation;
- verifies the public QR no longer returns an inactive response.

No Worker JavaScript/code deploy is performed by the package. Cloudflare Wrangler documents that `secret put` creates/deploys a Worker version containing the updated encrypted secret; this is a secret/config rotation, not a source-code replacement.

## Protected scope
Do not touch:
- web 3500
- protected dev 3457
- Google Sheet sync/parsers
- Timetable
- Test Monitor
- Sheet Updates
- QR slug/image
- QR destination during activation

## Acceptance
Do not promote this implementation to the clean production-working branch until the real Windows run reports:

`SUCCESS - QR smfffdy IS ACTIVE AND DYNAMIC`

If V2 fails after secret rotation, keep the newly rotated Cloudflare/local secret paired because the old Cloudflare secret value cannot be recovered; restore local source/DB and restore the original `smfffdy` edge route using the new secret.
