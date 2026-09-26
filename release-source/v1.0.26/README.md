# v1.0.26 - QR Scale + Analytics v2

This release is the actual QR scale solution requested on 2026-08-13.

## User requirement

- My QR Codes must not be bulky.
- Analytics must be a full commercial dashboard, not a small page.
- Design for lakhs of QR codes and approximately 100 lakh / 10,000,000 QR accesses/scans.
- Every QR must keep **Copy Source Link**, **Copy QR/Public Link**, and **Open/Show QR anytime**.
- Preserve QR PNG/SVG/PDF, edit, active/inactive, clear data, delete, templates, bulk generation, identity/verified-scan/anti-bot rules, styling and per-QR analytics.

## Implemented solution

- Server-side cursor/keyset QR listing, search, filters and sorting.
- Compact table-first QR library with optional compact cards and on-demand QR modal.
- Global Analytics v2 plus one-click per-QR drill-down.
- Aggregate-backed KPIs/trends/dimensions/top-QR queries.
- Cursor-paged raw scan history; no client loading of millions of scan rows.
- Bounded background scan aggregation. The raw QR redirect/scan request does not run dashboard aggregation work.
- Same-origin `/backend` bridge to the local API.

## Production data safety

Authoritative DB remains `D:\\timetable-intelligence-platform\\services\\api\\data\\timetable.db`.

The installer:
1. verifies production DB integrity and critical counts;
2. creates a consistent SQLite backup before source/service changes;
3. runs backend tests against an isolated temporary database;
4. runs TypeScript/tests/build before switching the runtime;
5. verifies critical production counts again after restart;
6. checks Today/Weekly/Sources/Sheet Updates/Test Monitor/QR/Analytics together;
7. rolls back on a blocking failure;
8. never touches protected port 3457.

## Runnable package

The exact distributable is stored in this branch at:

`packages/v1.0.26/timetable-intelligence-platform-v1.0.26-qr-scale-analytics-v2.zip`

SHA-256:

`1e363b5337292e3c9bfd83f1bbb16e25f50bd3e6a75539e910e8d8baeb0187ab`

Run after extracting:

`RUN_V1_0_26_NOW.cmd`

## Acceptance

Local/static/synthetic validation: PASS.

Real Windows acceptance: **PENDING**. Do not merge to stable `v1` until the real Windows installer completes without rollback and the complete app acceptance gate passes.