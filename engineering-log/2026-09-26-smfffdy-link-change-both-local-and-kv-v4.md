# 2026-09-26 — smfffdy same-QR link-change V4

## User-reported problem
The permanent tracked QR `https://q.nexttoppers.workers.dev/q/smfffdy` was not opening the newly edited destination. The user requires the same printed QR / same slug while changing only the destination URL.

## Diagnosis
The QR has two relevant pieces of state:
1. Local API/SQLite QR record (`target_url`, `active`)
2. Cloudflare remote KV route `qr:smfffdy`

Changing only the local record does not guarantee the edge route is updated. Earlier automatic edge-sync work was blocked by the missing/undeployable Worker secret/version state. V3 intentionally avoided Worker changes but still required a separate sync step after edits.

## V4 urgent fix
Created an interactive one-run tool that changes and verifies BOTH sides:
- PATCH existing QR id for slug `smfffdy` with only the new `target_url`.
- Preserve same QR id, same slug, Tracked mode and QR pixels.
- Ensure `active=true` if required.
- Write only remote KV key `qr:smfffdy` in namespace `nexttoppers_qr_edge` using authenticated Wrangler and `--remote`.
- Read the KV value back and require exact new `target_url` plus `active=true`.
- Probe public QR until the new target is visible, allowing for KV edge-cache propagation.
- If acceptance fails after the local update, attempt to restore the old local target/state and old edge route.

## Explicit non-scope
No web restart, no API restart, no protected port 3457, no Sheets, Timetable or Test Monitor change, no Worker JavaScript deployment, no Worker secret/version change, no other KV QR keys.

## Artifact
`NEXTTOPPERS_QR_SMFFFDY_CHANGE_LINK_NOW_V4.zip`
SHA-256: `2594beadcc3f287db8846cc3385132a9bb99b30230aa70b2fee35697f8a5063d`

Local package validation:
- ZIP CRC PASS
- Python syntax PASS
- self-test PASS (URL validation, same-slug route payload, namespace parsing)
- no API restart code
- no Worker deploy/secret command

## Cloudflare behavior relevant to acceptance
Wrangler v4 requires `--remote` for remote KV operations. KV is eventually consistent; recently cached values can remain visible until cache TTL expiry. The current Worker source uses a 30-second KV cache TTL, so public verification waits for edge propagation before success.

## Acceptance gate
Do not promote as production-working until real Windows run prints `SUCCESS - SAME QR LINK CHANGED` and the same printed QR opens the requested new destination.