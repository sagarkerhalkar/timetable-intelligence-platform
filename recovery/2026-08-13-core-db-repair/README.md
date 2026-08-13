# Timetable Core DB Recovery — preserve QR

Purpose: recover the normal Google Sheet / Today Timetable runtime after the 2026-08-13 working-directory/database split, without losing QR records.

Authoritative core DB:

`D:\timetable-intelligence-platform\services\api\data\timetable.db`

QR/root DB involved in the incident:

`D:\timetable-intelligence-platform\data\timetable.db`

The recovery scripts in this folder are designed to:

1. integrity-check both DBs;
2. back up both DBs and QR asset folders;
3. preserve the service/API DB's timetable/source/test/change/content/notification domain;
4. merge only `qr_templates`, `qr_codes`, `qr_scans` and missing `qr_assets` from the root DB;
5. pin `DATABASE_URL` to the absolute service/API DB path;
6. start Uvicorn from `services\api` on 3550 and web on 3500;
7. never touch protected port 3457;
8. verify API counts match the authoritative DB;
9. synchronously re-sync the four trusted timetable workbooks through the existing API;
10. validate Today timetable plus Sheet Updates, Test Monitor and QR API/page health.

Do not use the older recovery approach that starts the whole API from the project root merely to expose QR data.

The one-click Windows package is built from these scripts and should be run before any further QR/UI release is attempted.