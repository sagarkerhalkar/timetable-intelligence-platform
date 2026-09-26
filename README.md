# Timetable Intelligence Platform

Google Sheets-driven timetable, content search, sheet-update tracking, Test Monitor, notifications, and QR Studio for a Windows LAN server.

## Stable vs release candidate

- Stable working branch: `v1`
- Release-candidate branch: `v1.0.24-qr-templates-bulk-analytics`
- Current package: **v1.0.25 Paged UX + Larger QR Library**
- Do **not** treat the release-candidate branch as production until its Windows installer completes the full regression/typecheck/build/runtime gate without rollback.

## Current QR workflow

`New QR -> Templates -> Bulk Create -> My QR Codes -> Analytics`

v1.0.24 introduced reusable server-side templates, bulk Name + URL creation, and independent per-QR analytics.

v1.0.24.1 corrected the Bulk parser for the project's real `strict` + `noUncheckedIndexedAccess` TypeScript contract.

v1.0.25 is a focused UI release:
- shared pagination for long QR collections;
- My QR Codes: 8 larger QR cards/page;
- actual QR preview on every card plus large `Show QR` modal;
- Copy Source Link and Copy QR Link with LAN/older-browser fallback;
- checkbox selection across pages and `Delete Selected`;
- Templates: 6/page;
- Bulk template chooser: 6/page;
- Bulk input rows: 10/page;
- Bulk generated results: 10/page;
- Device Intelligence: 6 devices/page;
- Recent Scan History: 15 rows/page.

No tracking, analytics, Wi-Fi, identity, template or timetable semantics are changed by v1.0.25.

## Continuation docs

Read these first in a new chat/development session:

1. `docs/CURRENT_PROJECT_CONTEXT.md`
2. `docs/QR_PLATFORM_ARCHITECTURE.md`
3. `docs/V1_0_24_QR_TEMPLATES_BULK_ANALYTICS.md`
4. `docs/V1_0_24_1_STRICT_TYPESCRIPT_FIX.md`
5. `docs/V1_0_25_PAGINATION_QR_LIBRARY.md`
6. `reports/VALIDATION_V1_0_25.md`

The public repository intentionally excludes databases, credentials, recipient data, private Sheet contents, runtime logs, cookies/tokens and uploaded customer assets.
