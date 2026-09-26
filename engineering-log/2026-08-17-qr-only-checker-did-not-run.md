# 2026-08-17 - QR-only checker did not run

## User report
The user reported that running the QR-only read-only checker resulted in nothing happening.

## Decision
Do not ask the user to run another ZIP/checker package. Use one direct, read-only PowerShell/Python command instead.

## Safety
The direct command only opens the authoritative service DB in SQLite read-only mode and prints integrity, qr_codes count, and the latest QR records. It does not restart services, write to the DB, deploy/rollback the Worker, or modify KV/source.

## Frozen scope
The currently working Sheets, Time Table, Test Monitor, Sheet Updates, and other app pages must remain untouched. Work only on QR after identifying the QR record state.

## Next action
Ask the user to paste the direct command output. Determine whether new QR records are still in services/api/data/timetable.db before any QR-only change.