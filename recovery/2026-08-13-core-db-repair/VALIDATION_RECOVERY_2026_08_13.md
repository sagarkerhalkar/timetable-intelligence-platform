# Timetable Core DB Recovery Validation — 2026-08-13

## Evidence reviewed

Windows runtime showed two different database files:

- `D:\timetable-intelligence-platform\services\api\data\timetable.db` — 41,881,600 bytes
- `D:\timetable-intelligence-platform\data\timetable.db` — 62,636,032 bytes

A previous recovery script explicitly started Uvicorn from the project root so the relative default `sqlite:///./data/timetable.db` selected the root DB. That explains the observed state: recovered QR data partly works while timetable/Google Sheet state is inconsistent.

## Recovery contract

- service/API DB remains authoritative for timetable/source/test/change/content/notification data;
- root DB is treated only as a QR recovery source;
- only `qr_templates`, `qr_codes`, `qr_scans` and missing QR PNG assets are merged;
- both DBs are backed up with SQLite's backup API before modification;
- duplicate QR slugs and foreign-key violations abort the merge transaction;
- `.env.local` is backed up and `DATABASE_URL` is pinned to the absolute service/API DB path;
- API is started from `services\api` on 3550;
- web remains on 3500;
- port 3457 is never touched;
- all four trusted timetable Sheet IDs are required before sync;
- Today, Sheet Updates, Test Monitor and QR endpoints are validated together.

## Local validation

- Python helper `py_compile`: PASS.
- Synthetic split-DB test: PASS.
- Synthetic test using the actual v1.0.24.1 SQLite schema: PASS.
- Core `sources` and `timetable_entries` remained unchanged while QR template/code/scan rows were imported: PASS.
- SQLite `foreign_key_check` after merge: PASS.
- PowerShell and CMD files are ASCII-only to avoid Windows PowerShell 5.1 UTF-8 parser corruption: PASS.

## Not claimed

The real Windows database contents and live Google Sheet sync cannot be executed in the packaging environment. The one-click recovery run on the Windows server is authoritative.