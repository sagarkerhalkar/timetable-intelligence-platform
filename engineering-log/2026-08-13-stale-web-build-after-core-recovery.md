# 2026-08-13 - Stale Web Build After Core/Google Sheet Recovery

## User-visible state

After emergency database recovery, QR data was visible again but the user still saw the old/empty timetable UI and reported that Google Sheet / Today Timetable looked unrecovered.

## Evidence

The authoritative recovery report `TIMETABLE_CORE_RECOVERY_20260813_162409.txt` shows the backend/core recovery itself completed successfully:

- correct service/API database active;
- QR data preserved;
- Google Sheets synced;
- `/timetable?view=today` HTTP check PASS;
- `/timetable?view=week` PASS;
- `/sources` PASS;
- `/changes` PASS;
- `/tests` PASS;
- `/qr/codes` PASS.

Therefore the remaining user-visible mismatch is not another database-loss event. The screenshots/current UI indicate a stale old Next.js build (reported as v1.0.11.1/empty-looking screens) remained on web port 3500 after prior rollback/recovery.

## Root cause

A previous recovery restored an old `.next` build while repairing the database split. The backend later returned to the correct service/API database and successfully synced Sheets, but the web process continued serving the stale compiled Next.js output.

## Immediate fix

A web-only recovery package was created: `FIX_STALE_TIMETABLE_WEB_BUILD_NOW.zip`.

Safety contract:

- does not modify either SQLite database;
- does not stop API port 3550;
- does not change QR records;
- does not change Google Sheet/core data;
- does not touch protected port 3457;
- requires the authoritative service DB to contain at least 4 source workbooks, substantial timetable rows, and at least 24 recovered QR records before touching web;
- verifies API core endpoints before rebuild;
- backs up the existing `.next` folder;
- stops only Node on port 3500;
- deletes stale `.next` and runs `npm run build` from the current `apps/web` source;
- starts the rebuilt web on 3500;
- verifies Today, Week, Sources, Sheet Updates, Tests and QR pages;
- re-verifies DB/API/QR state after rebuild;
- automatically restores the previous `.next` build if the new build fails.

Package SHA-256: `ad6f7c2aedfdf0e12f06d9717d3a0a6156de6ad040a99bebd55fdc22e5cfcbb1`.

## Release status

All v1.0.25 feature work remains stopped until the existing application is visibly restored for the user. Stable `v1` remains untouched.
