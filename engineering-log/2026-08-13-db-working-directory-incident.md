# 2026-08-13 — DB working-directory incident and recovery plan

## Evidence from Windows

Current runtime inspection showed two distinct DB files:

- `services\api\data\timetable.db` — 41,881,600 bytes
- `data\timetable.db` — 62,636,032 bytes

Ports at inspection time:
- 3500 -> `node.exe` PID 21696
- 3550 -> `python.exe` PID 22656

The prior recovery had made QR partly usable but timetable/Google Sheet logic became incorrect.

## Root cause found

The app's default DB setting is relative (`sqlite:///./data/timetable.db`). The prior recovery explicitly started Uvicorn with project root as working directory to use the larger/root DB because it contained recovered QR rows. That changed the entire API DB, not only QR storage.

This was the wrong recovery architecture: QR recovery must never redirect timetable/source/test/change/content state to a second database.

## Corrective design

- service/API DB is authoritative core;
- both DBs integrity-checked and backed up;
- QR-only tables/assets merged into core DB;
- core tables never copied from QR/root DB;
- `DATABASE_URL` pinned to absolute service/API DB path;
- API started from `services\api`;
- API source/QR counts verified against core DB;
- four trusted Sheets re-synced via existing source-sync endpoint;
- Today, Sheet Updates, Test Monitor and QR checked together;
- port 3457 untouched.

## Validation before package

- recovery Python helper compiles;
- synthetic merge test preserves core `sources`/`timetable_entries` while importing QR tables;
- actual v1.0.24 QR schema synthetic merge passes `foreign_key_check`;
- PowerShell/CMD recovery scripts contain ASCII only to avoid Windows PowerShell 5.1 encoding/parser issues;
- real Windows runtime remains authoritative.

## Next action

Run `RUN_RECOVER_TIMETABLE_CORE_PRESERVE_QR.cmd` from the recovery package. If it fails, upload `TIMETABLE_CORE_RECOVERY_*.txt`. Do not install another QR/UI release until recovery passes.