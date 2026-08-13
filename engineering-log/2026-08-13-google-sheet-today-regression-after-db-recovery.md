# 2026-08-13 - Google Sheet Today regression after QR database recovery

## User-visible state

After the failed v1.0.25.1 installer and subsequent database-path recovery, the user's existing QR library became visible again. The read-only database scan proved the populated production database at `D:\timetable-intelligence-platform\data\timetable.db` still contains **24 QR codes, 19 scans, and 1 QR template**.

However, after QR recovery the user reported that Google Sheet-driven **Today Timetable** data was no longer working. The user explicitly requested the fully working old application back, not further feature installation.

## Important historical contract

Earlier stable timetable releases preserve the SQLite database/source connections and use the application's own serialized Google Sheet sync flow. Old successful Sheet data is supposed to remain visible until a successful replacement is ready. Live Sheet refresh is not supposed to cause destructive rollback of unrelated data.

## Current assessment

- QR records are present; this is not a QR deletion incident anymore.
- The v1.0.25 UI payload is not being pursued during recovery.
- The current issue is the Google Sheet -> SyncService -> local database -> Today Timetable flow.
- The current populated database must remain authoritative and must not be replaced by an empty `services\api\data\timetable.db`.
- No claim is made yet that the exact Sheet-sync root cause is fixed until the live Windows sync result is observed.

## Recovery action supplied

A non-destructive Sheet-sync recovery tool was created:

`RESTORE_GOOGLE_SHEETS_AND_TODAY_TIMETABLE.zip`

It does not modify application source and does not install v1.0.25. It:

1. verifies SQLite integrity;
2. requires at least 24 current QR records before proceeding;
3. creates a consistent backup of the populated database;
4. reads `/api/v1/sources`;
5. discovers the application's existing POST sync/refresh/check endpoints from `/api/openapi.json`;
6. queues normal application Sheet sync for enabled sources;
7. polls source status and preserves exact `last_error` messages;
8. checks Today Timetable for civil date `2026-08-13` overall and for Commerce, Science, Humanities and Nirmaan;
9. verifies QR count again after sync;
10. writes a Desktop diagnostic report.

## Safety

- No v1.0.25 source is applied.
- No QR code is deleted.
- No database is replaced.
- Ports 3500/3550 are not stopped by this sync tool.
- Protected port 3457 is untouched.
- The database is backed up before normal Sheet sync is requested.

## Required next evidence

The live Windows output/report from `RUN_RESTORE_GOOGLE_SHEETS_TODAY.cmd` is authoritative. If all sources finish `success` and Today returns rows, the Sheet/Today recovery is PASS. If a source returns an error, preserve the exact error and fix only that runtime/config/sync issue before any future QR release work.

## Release policy

Do not resume v1.0.25/v1.0.25.x feature installation until QR, Google Sheet sync, Today Timetable, Test Monitor and Sheet Updates are all confirmed working again on the restored application.