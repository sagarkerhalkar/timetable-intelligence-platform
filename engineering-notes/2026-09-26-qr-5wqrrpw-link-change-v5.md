# QR 5wqrrpw urgent link-change diagnosis and V5

## User-visible problem
Permanent QR URL:
`https://q.nexttoppers.workers.dev/q/5wqrrpw`

Observed old destination:
`https://www.youtube.com/watch?v=TmrkmcY9flc`

Requested new destination:
`https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`

## Root cause
The previous V4 emergency helper was hard-coded for slug `smfffdy`. It could not update Cloudflare KV key `qr:5wqrrpw`. Therefore a local QR edit for `5wqrrpw` could coexist with the old edge KV route, and the public scan continued to open the old YouTube URL.

## V5 acceptance contract
- Preserve QR slug `5wqrrpw` and QR id.
- Preserve tracked/dynamic mode.
- Set local `target_url` to `https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`.
- Ensure `active=true`.
- Overwrite only remote KV key `qr:5wqrrpw` in existing `nexttoppers_qr_edge` namespace.
- Read the KV key back and require the requested new URL and `active=true`.
- Verify the public QR exposes the new target after edge-cache propagation.
- No QR regeneration or reprint.
- No API restart.
- No Worker code deployment, Worker secret change, or Worker version change.
- No Sheets/Timetable/Test changes.

## Package
`NEXTTOPPERS_QR_5WQ_RRPW_URGENT_LINK_FIX_V5.zip`

Package SHA-256:
`e1c9f2195e81bee200f65600f54f5f78749103b294b82f44806778ecbe0485d8`

Local package validation:
- ZIP CRC PASS
- exact slug/target self-test PASS
- no API restart code
- no Worker deploy/secret modification

Production acceptance remains pending until the Windows server run returns `SUCCESS - SAME QR 5wqrrpw LINK CHANGED` and the same printed QR opens the requested new YouTube URL.
