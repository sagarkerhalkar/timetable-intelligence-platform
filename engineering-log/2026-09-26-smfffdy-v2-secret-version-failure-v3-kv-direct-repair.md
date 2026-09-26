# smfffdy urgent QR repair: V2 Cloudflare secret/version failure and V3 direct-KV correction

Date: 2026-09-26
Branch: `nexttoppersqr`
Permanent QR: `https://q.nexttoppers.workers.dev/q/smfffdy`

## Confirmed live state from Windows

- API 3550 serves `D:\timetable-intelligence-platform\data\timetable.db`.
- `smfffdy` exists exactly once in the live API.
- QR id: `d7633372b13d92c7a691fad1`.
- Local QR state is already `active=True`.
- Existing destination is preserved.
- The service DB copy did not match the running API and must not be switched in this repair.

## V2 result

V2 created source/DB safety backup, completed Wrangler login, and then Cloudflare rejected `wrangler secret put NEXTTOPPERS_EDGE_SYNC_SECRET --name q` with:

`Secret edit failed. You attempted to modify a secret, but the latest version of your Worker isn't currently deployed.`

The installer restored the pre-fix local QR source and live DB and restarted the previous API baseline successfully. No accepted QR change came from V2.

## Why V3 changes approach

Do not deploy an unknown/latest Worker version merely to rotate a secret. The immediate outage is caused by a stale edge route combined with the local fast resolver omitting the `active` field. The currently deployed Worker already has a fallback path that resolves from the origin and writes a valid route back to KV.

V3 therefore avoids Worker secret/version changes completely:

1. Back up `qr_fast.py` and the live DB.
2. Add `active: bool(row["active"])` to successful qr-fast resolve responses.
3. Restart only API 3550 with the already-served DB pinned explicitly.
4. Verify `/api/v1/qr-fast/smfffdy/resolve` returns `active=true` with the same target.
5. Use authenticated Wrangler KV access to discover the existing `nexttoppers_qr_edge` namespace.
6. Overwrite only remote key `qr:smfffdy` with the current live QR route (`active=true`, same slug, same target).
7. Wait for the old edge-cache value to expire and verify the public QR no longer reports inactive.

No Worker JavaScript, Worker secret, Worker deployment/version, KV namespace, other QR key, web 3500, protected 3457, Sheets, Timetable, or Test Monitor is changed.

## Same QR / changeable destination requirement

The slug `smfffdy` is permanent and must never be regenerated for destination changes. During the urgent phase V3 includes a helper that re-syncs only `qr:smfffdy` to edge KV after the destination is edited in the existing QR UI. This preserves the same printed QR. Automatic edit-to-edge sync will be finalized only after the Worker version/secret state is reconciled safely.

## V3 artifact

`NEXTTOPPERS_QR_SMFFFDY_URGENT_FIX_V3.zip`

SHA-256: `2444433eafd05407fec0947abbb21c82e0440b4bee023d68d1b3f391945e7b53`

Local validation before delivery:

- ZIP CRC: PASS
- qr-fast patch syntax: PASS
- patch idempotency: PASS
- no Worker secret command in V3: PASS
- no Worker deploy/version command in V3: PASS
- cloud remote write scope: only KV key `qr:smfffdy`

Real Windows acceptance is pending the user run and must not be claimed until the success output is observed.
