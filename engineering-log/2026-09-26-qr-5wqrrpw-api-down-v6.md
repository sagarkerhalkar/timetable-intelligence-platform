# 2026-09-26 — QR 5wqrrpw API-down recovery V6

## User-visible failure
`RUN_5WQ_RRPW_URGENT_FIX_NOW.cmd` stopped safely because API 3550 was not healthy.

Exact QR that must remain unchanged:
- `https://q.nexttoppers.workers.dev/q/5wqrrpw`

Observed old destination:
- `https://www.youtube.com/watch?v=TmrkmcY9flc`

Required destination:
- `https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`

## Important application behavior
URL QR destinations are persisted in two local fields:
- `qr_codes.target_url`
- `qr_codes.payload_json["url"]`

Both must be changed together. The printed/tracked QR slug must not be regenerated.

## V6 strategy
V6 does not require API 3550 to be healthy.

It:
1. Finds slug `5wqrrpw` in the two known SQLite DB locations.
2. Creates full SQLite backups before each write.
3. Updates only that QR row: `target_url`, `payload_json.url`, `active=1`.
4. Uses Wrangler production deployment/version metadata to discover the KV namespace actually bound to the deployed Worker variable `QR_EDGE`; it does not guess by namespace title.
5. Writes and reads back only `qr:5wqrrpw` in the production-bound namespace(s).
6. Verifies the public Worker exposes the new YouTube destination before reporting success.
7. Tries to recover API 3550 only if the port is completely free; it will not kill an unhealthy/unknown listener.

## Safety scope
Not changed:
- printed QR / slug
- web 3500
- protected dev 3457
- Google Sheets
- timetable/test data other than the single QR row
- Worker JavaScript
- Worker secrets
- Worker deployment/version
- other KV QR keys

## Package
`NEXTTOPPERS_QR_5WQ_RRPW_API_DOWN_FIX_V6.zip`

Local package validation before delivery:
- ZIP CRC PASS
- Python self-test PASS
- direct DB route logic PASS
- production `QR_EDGE` binding-discovery parser PASS

Real Windows acceptance is pending user execution. Do not promote as production-working until the user reports the V6 success line and scan verification.
