# Incident 2026-08-13 — database working-directory split broke timetable while QR partly worked

## Symptom

After a recovery performed in another development chat, QR data was partly visible but Google Sheet / Today Timetable / other timetable logic became inconsistent.

The Windows runtime showed two different SQLite files:

- `D:\timetable-intelligence-platform\services\api\data\timetable.db`
- `D:\timetable-intelligence-platform\data\timetable.db`

The recovery had intentionally started Uvicorn with the project root as its working directory to make the root DB visible for recovered QR records.

## Root cause

`services/api/app/config.py` defaults to:

`DATABASE_URL=sqlite:///./data/timetable.db`

That path is relative to the API process working directory.

Therefore:

- normal API working directory `D:\timetable-intelligence-platform\services\api` resolves to `services\api\data\timetable.db`;
- starting the same API from `D:\timetable-intelligence-platform` resolves to root `data\timetable.db`.

The root-DB recovery solved one symptom (QR visibility) by switching the entire API to a different database. That bypassed the normal timetable/source database and caused the timetable/Google Sheet state to diverge.

## Permanent rule

**The authoritative application/core database is `services\api\data\timetable.db`.**

Never restore QR data by starting the whole API against `D:\timetable-intelligence-platform\data\timetable.db`.

If QR rows/assets exist in another valid DB, merge only QR-domain data into the authoritative core DB:

- `qr_templates`
- `qr_codes`
- `qr_scans`
- missing PNG files under `qr_assets`

Do not replace from the QR/root DB:

- `sources`
- `timetable_entries`
- `changes`
- `test_records`
- `content_items`
- `workbook_profiles`
- notification data

## Recovery design

The 2026-08-13 recovery package under `recovery/2026-08-13-core-db-repair/`:

1. integrity-checks both DBs;
2. stops only Timetable ports 3500/3550 and never touches 3457;
3. makes consistent backups of both DBs and QR asset folders;
4. keeps the service/API DB as the timetable core;
5. merges QR-only tables and missing assets from the root DB;
6. pins `DATABASE_URL` to the absolute service/API DB path in `.env.local` while preserving all other lines;
7. starts Uvicorn from `services\api`;
8. verifies API source/QR counts match the authoritative DB;
9. re-syncs the four trusted timetable workbooks via the existing API;
10. validates Today timetable, Sheet Updates, Test Monitor and QR endpoints.

## Trusted timetable sources

- Humanities: `1M8mxrLzxZ9AixQ7fejbzIjhZGLgNzS7flMx6cXgiXHQ`
- Science: `1j1yR4DRzqJwnkkfHmeWuv7vP-iDP0KZVahV4l9lcjEg`
- Commerce: `1vEGv2nzGYlFWtHT8SmvzGIYeL_Yl9RJNRohM2VHY0Lg`
- Nirmaan: `1a7qJpddbGL3fnR6RBmsrFxqjjVLB_g9Ryz7cQ1i0W8U`

## Release rule

No new QR/UI release should be installed until this recovery succeeds and the timetable Google Sheet flow is proven healthy again.

Stable `v1` must not be updated merely because QR works. Timetable core + Google Sheet sync + Test Monitor + Sheet Updates + QR must pass together before a release is accepted.