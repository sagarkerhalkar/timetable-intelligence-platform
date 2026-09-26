# 2026-08-17 - QR DB split confirmed; QR-only restore prepared

## User requirement
- Freeze the currently working Sheets, Timetable, Test Monitor, Sheet Updates and other app pages.
- Work on QR only.
- New QR state must survive reboot.
- QR redirect target remains <=0.6 seconds for the redirect response; speed work is separate from this data recovery.

## Confirmed post-reboot runtime
User-provided read-only evidence confirmed:
- web 3500 running Next.js from `D:\timetable-intelligence-platform\apps\web`
- API 3550 running uvicorn
- protected 3457 not listening
- Worker `https://q.nexttoppers.workers.dev` is live with `x-ntqr-fast=3`, `x-ntqr-source=edge-kv`

## Exact QR database split
New QR/service DB:
`D:\timetable-intelligence-platform\services\api\data\timetable.db`
- integrity: ok
- qr_codes: 23
- qr_scans: 4
- qr_templates: 3
- latest examples created 2026-08-14: Economics 12th `vg3785v`, Economics 11th `mb365th`, physics 12th `f336c43`

Current root DB:
`D:\timetable-intelligence-platform\data\timetable.db`
- integrity: ok
- qr_codes: 24
- qr_scans: 24
- qr_templates: 1
- older examples created 2026-08-12: Biology 11th `s66s4bb`, Applied Maths 12th `rkph34u`, Applied Maths 11th `mw9jmyn`

The user then called `GET http://127.0.0.1:3550/api/v1/qr-codes`. The response had `Count: 24`, returned the older root slugs and `public_base_url=https://nexttoppers.sagarkerhalkar.com`. This proves the rebooted API is currently serving the root DB QR tables, not the newer service DB QR tables.

## Why whole-API DB switching is prohibited
The rest of the app is currently working and the user explicitly wants it preserved. Historic project incident documentation also records the relative SQLite/workdir split. Therefore this recovery must not switch the whole API database just to expose QR.

## QR-only recovery design
Prepared package: `NEXTTOPPERS_QR_NEW_SET_RESTORE_ONLY.zip`
SHA-256: `d02b9f29ea345c44592cdcadf8bf2c03d49c65ba2a06d63e66dfcec26c32fd0d`

The package:
1. verifies both DB integrity and foreign keys;
2. verifies running `/api/v1/qr-codes` exactly matches the current root QR slug set before writing;
3. verifies the service QR set is newer than the root QR set;
4. creates full SQLite safety backups of both DBs;
5. replaces only `qr_templates`, `qr_codes`, `qr_scans` in the root DB from the newer service DB;
6. uses `BEGIN IMMEDIATE` and checks core-table row counts plus non-QR schema fingerprint inside the same transaction;
7. verifies root QR fingerprint exactly equals the service QR fingerprint after write;
8. verifies the running API exposes exactly the new QR slug set within 20 seconds;
9. restores the previous root QR tables from backup if acceptance fails after the write.

## Explicitly untouched
- sources
- cells
- timetable_entries
- content_items
- test_records
- changes
- web source/build
- API source
- API process
- web process
- Cloudflare Worker
- Cloudflare KV
- port 3457

## Local validation before delivery
- ZIP CRC: PASS
- Python syntax: PASS
- synthetic QR-only replacement: PASS
- core-table preservation test: PASS
- no process restart code: PASS

## Next action
Run the QR-only restore package on Windows. On success refresh the QR page with Ctrl+F5 and verify the newest 14-Aug QR records are visible. Only after this data recovery is accepted should the separate Worker <=0.6-second direct-redirect optimization be applied.
