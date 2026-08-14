# NextToppers QR Edge KV v1.0.29

Observed real-phone performance after v1.0.28.1 remained about 5-8 seconds.

## Cause

The Worker still synchronously called `https://nexttoppers.sagarkerhalkar.com/backend/api/v1/qr-fast/<slug>/resolve` with `cache: "no-store"` before every tracked scan response. This kept the Cloudflare Tunnel/local API round trip in the user's critical path. The scan page also retained an intentional redirect delay.

## Fix

- Route lookup is stored in Cloudflare Workers KV binding `QR_EDGE`.
- Normal KV-hit scan does not synchronously call the local API/Tunnel.
- API `qr_fast.py` syncs changed/deleted QR routes to a protected Worker admin endpoint every second.
- Sync secret is generated on the Windows server and configured as a Worker secret; it is never stored in GitHub.
- Anonymous tracked redirect delay is capped at 120 ms.
- Analytics persistence remains asynchronous through `ctx.waitUntil()`.
- Smart Placement is removed because the normal route lookup now runs at Cloudflare edge KV rather than near the origin.
- KV miss falls back to the existing resolver and warms KV.

## Safety

No SQLite migration/delete/replace. Web 3500 is not stopped. Protected port 3457 is untouched. Full backend pytest runs against an isolated temporary database before runtime switch. Worker JavaScript syntax is checked before deployment. API/Worker rollback is attempted on post-deploy acceptance failure.

## Artifact

`NEXTTOPPERS_QR_EDGE_KV_V1_0_29.zip`

SHA-256: `6953d2fe3bf842e60e0c4822624ddc2e41490346fa7ce12e70fb4ab68081fe11`

ZIP CRC: PASS. Python syntax: PASS. Worker JS syntax: PASS.

Windows/phone acceptance is pending. Do not mark v1.0.29 accepted until the installer reports an actual `x-ntqr-source: kv` sample and the phone timing is materially below 5-8 seconds.
