# 2026-08-17 - Freeze current working app; QR-only scope

## User-confirmed current baseline
After machine restart, the old application build is visible again. The user reports that this restored/current baseline is GOOD and must be preserved:
- old Google Sheet data is appearing correctly
- Time Table works
- Test Monitor works
- other application options work correctly

## Locked scope from this point
Do NOT modify or replace the working baseline modules above.

Only QR needs investigation/change:
- restore/bring forward the newer QR Studio/UI/records as required
- preserve current working Sheet/Time Table/Test Monitor behavior
- QR redirect target: <=0.6 s for the redirect response where network/destination permits
- persist the correct QR module across Windows restart

## Why old QR/UI likely reappeared
Recent QR deployment packages did not reach accepted state and triggered rollback. On reboot, the persisted/autostart web/API configuration therefore launched the previously accepted working application build. This explains why the rest of the application is now working correctly while the QR module appears old.

Do not infer that new QR database rows were deleted. QR UI/code rollback and QR record persistence are separate concerns. Before any QR-only write, inspect the active startup paths, active DB path, QR row counts/slugs, and web QR source so only the QR module is changed.

## Safety rule
No future QR fix may restart/replace Sheet parser, timetable, Test Monitor, Sheet Updates, or unrelated application UI. Protect port 3457 and current production database. Back up before QR-only changes and verify reboot persistence before acceptance.