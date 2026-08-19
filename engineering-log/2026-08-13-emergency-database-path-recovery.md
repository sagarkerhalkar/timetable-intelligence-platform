# 2026-08-13 - Emergency database-path recovery after v1.0.25.1 rollback

## Incident

The user reported that after the v1.0.25.1 acceptance failure/rollback, not only My QR Codes but also timetable/application data appeared missing. This was treated as a data-recovery incident and feature work was stopped.

## Read-only recovery evidence

A read-only SQLite scan over `D:\timetable-intelligence-platform` found the populated database still exists at:

`D:\timetable-intelligence-platform\data\timetable.db`

Observed live recovery candidate counts:

- `qr_codes = 24`
- `qr_scans = 19`
- `qr_templates = 1`

Multiple older backup databases also contain earlier QR data. Therefore the QR records were not proven deleted.

The scan also found older/empty databases under historical backup/runtime paths, including `services\api\data\timetable.db` variants without the current QR tables/data.

## Root cause hypothesis supported by installer code

The v1.0.25.1 rollback/start function launches Uvicorn with:

- working directory: `D:\timetable-intelligence-platform\services\api`
- module: `app.main:app`

The application database configuration uses a relative `data\timetable.db` runtime path. Restarting from `services\api` can therefore bind the API to `D:\timetable-intelligence-platform\services\api\data\timetable.db` instead of the populated repository-root database at `D:\timetable-intelligence-platform\data\timetable.db`.

This explains why the API could return healthy while timetable/QR data appeared empty.

## Emergency recovery package

Created a one-purpose recovery tool:

`EMERGENCY_RESTORE_TIMETABLE_AND_QR_DATA.zip`

Safety behavior:

1. Does not run any v1.0.25 installer.
2. Does not touch protected port 3457.
3. Does not stop web port 3500.
4. Reads the populated root database first.
5. Creates timestamped backups of BOTH root and API DB locations, including WAL/SHM sidecars when present.
6. Stops only API port 3550.
7. Uses Python `sqlite3.Connection.backup()` to make a consistent SQLite copy from the populated root DB into the API runtime DB path.
8. Requires SQLite integrity check `ok` and at least 24 QR records before restart.
9. Starts only API 3550 and verifies `/api/v1/dashboard` responds.

Package SHA-256:

`cca15c313cf7081124b009a11fc501fd6a6ec53c772e3d8baff3119c67c9a929`

## Important installer defect discovered

v1.0.25.1 backed up changed frontend source and `.next`, but did not back up the active production SQLite database or record the resolved runtime DB path before stopping/restarting services. This is a release-safety defect.

## Mandatory rule added for future installers

Before any future installer changes source or restarts services it must:

- resolve and print the exact active database path;
- run SQLite integrity check;
- record QR/timetable/source counts;
- create a consistent SQLite backup using the SQLite backup API;
- record backup SHA-256;
- after restart, verify the API is using the same intended database and that critical pre-install counts/data still exist;
- rollback database + source if a blocking gate fails;
- never infer a relative DB path from a changed working directory.

## Status

Emergency recovery package delivered to user first because they needed QR functionality urgently. v1.0.25 feature work remains paused until existing timetable/QR data is visibly restored and verified on the Windows machine.
