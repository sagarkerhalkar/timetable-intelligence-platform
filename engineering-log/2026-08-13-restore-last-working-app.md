# 2026-08-13 - Restore last working Timetable Intelligence app

## Urgent user requirement
The user needed the previously working application back immediately, with timetable and QR functionality available, and did not want another feature installer or partial/emergency-only database operation.

## Recovery evidence
Read-only scan proved the populated database still exists at `D:\timetable-intelligence-platform\data\timetable.db` with 24 QR codes, 19 scans and 1 QR template.

## Root cause
The v1.0.25.1 rollback restored frontend source/.next but restarted Uvicorn with working directory `D:\timetable-intelligence-platform\services\api`. The application uses a relative `data\timetable.db` path, so this can resolve to `services\api\data\timetable.db` instead of the populated root database. That explains why API health could be true while timetable/QR data appeared missing.

## Full restoration package
`RESTORE_LAST_WORKING_TIMETABLE_INTELLIGENCE_APP.zip`

SHA-256: `f5c030991f972209922f6fe75aad0aa12f36f3b1b01312e841c76284f3ebe8a4`

The package does NOT install v1.0.25. It:
1. requires root DB integrity and at least 24 QR records before any change;
2. creates a new safety backup of the populated root DB;
3. stops only ports 3500/3550;
4. restores the newest exact pre-v1.0.25.1 QR source and `.next` build from `_release_backups\v1.0.25.1_*` when available;
5. starts API from application root with `PYTHONPATH=D:\timetable-intelligence-platform\services\api`, so relative `data\timetable.db` resolves to the populated root DB;
6. starts web on 3500;
7. verifies Dashboard API, Timetable API, web root and My QR Codes page;
8. verifies the root DB still contains at least 24 QR records after restart;
9. never touches protected port 3457.

## Status
Feature work remains paused until the restored app is visibly working. No v1.0.25 installer should be run before the user confirms timetable and QR data are back.
