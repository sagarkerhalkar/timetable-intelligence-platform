# Urgent all-Sheets + web-build recovery — 2026-08-13

The previous core-DB recovery produced a false-positive user experience: the API successfully exposed four trusted sources and Today timetable rows, but the browser still served an old v1.0.11.1 production build showing `0 of 0` Google Sheets and `0 classes`.

The real Windows recovery report showed the authoritative service/API DB had 4 sources while the newer/root DB had 8 source registrations. Page validation only checked HTTP 200, so it did not prove that rendered content reflected the current API state.

This recovery therefore:

1. backs up both DBs, `.next`, `.env.local`, and changed web source;
2. stops only ports 3500/3550; port 3457 remains protected;
3. merges **all source registrations** from `D:\timetable-intelligence-platform\data\timetable.db` into the authoritative `services\api\data\timetable.db` while preserving existing core source IDs;
4. guarantees the four official timetable sources;
5. does **not** import root timetable/content/test/change/notification tables and does not modify QR tables;
6. pins the absolute core DB path;
7. syncs Humanities, Science, Commerce and Nirmaan first, then all additional enabled registered Sheets;
8. requires Today API to contain real rows;
9. applies known later cumulative Today/Sheet Updates/Test Monitor/navigation web source;
10. removes stale `.next` and runs real `npm run typecheck` + `npm run build` on Windows;
11. starts the fresh build and checks Today, Weekly, Google Sheets, Sheet Updates, Test Monitor and QR pages.

Run source files in this folder only after reviewing the corresponding validation document. Stable `v1` must not be updated until the real Windows recovery is verified.