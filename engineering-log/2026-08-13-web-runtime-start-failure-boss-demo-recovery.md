# 2026-08-13 - Web runtime start failure after successful rebuild

## User impact
User urgently needed to demonstrate the app to their boss. QR, timetable, tests and Sheet data appeared unavailable in the UI after prior recovery attempts.

## Authoritative Windows evidence
The latest recovery run proved the service/API database itself is healthy and populated:
- SQLite integrity: `ok`
- sources: `4`
- timetable_entries: `989`
- test_records: `1122`
- changes: `95`
- qr_codes: `24`
- qr_scans: `24`
- `/api/v1/dashboard`: HTTP 200
- `/api/v1/sources`: HTTP 200
- `/api/v1/timetable?page=1&page_size=1`: HTTP 200

The web source also built successfully with Next.js 16.2.12, TypeScript passed and all 16 routes were generated. The failure occurred only after build when the recovery script started the production web process on port 3500; health check never became ready. The script then rolled back the prior `.next` build successfully.

## Conclusion
Business data is not lost. The remaining blocker is the web runtime/start layer on port 3500, not SQLite corruption or Google Sheet data loss.

## Immediate boss-demo recovery
Created `START_FULL_CURRENT_APP_FOR_BOSS_NOW.zip` to bypass the unreliable `npm start` production wrapper without modifying business data.

The launcher:
1. verifies the authoritative service DB still has >=4 sources, >=500 timetable entries, >=500 tests, >=1 change and >=24 QR codes;
2. verifies API 3550 core endpoints;
3. stops only the Node listener on port 3500;
4. starts the current `apps/web` source directly with Next.js dev mode using `node.exe node_modules/next/dist/bin/next dev -H 0.0.0.0 -p 3500`;
5. verifies Home, Today, Week, Sources, Sheet Updates, Tests and My QR Codes;
6. re-verifies database/API state.

It does not modify either SQLite DB, does not stop API 3550 and does not touch protected port 3457.

Package SHA-256: `a80302ac6da86c3c55f76cf2aefdf34175a74c4fc93f6c47b021a38d91b50598`.

## Next action
User should run `RUN_START_FULL_APP_FOR_BOSS_NOW.cmd`. If it fails, use the generated Desktop `BOSS_DEMO_START_*`, `BOSS_DEMO_WEB_*.log` and `BOSS_DEMO_WEB_*.err.log` files to identify the exact Node/Next runtime failure. Do not run another release installer until the normal production-start root cause is fixed.