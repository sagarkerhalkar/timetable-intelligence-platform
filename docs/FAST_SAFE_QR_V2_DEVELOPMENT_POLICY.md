# Fast + Safe Development Policy — QR Scale + Analytics v2

Status: **MANDATORY** for the next QR Scale + Analytics v2 work and every follow-up session unless explicitly superseded.

## User requirements locked on 2026-08-13

- Replies and code delivery must stay fast; do not spend 1–3 hours on repeated investigation or GitHub bookkeeping before providing validated working code.
- GitHub must stay updated in the same development turn so a new chat can continue without reconstructing today’s mistakes.
- Every material command/action must be represented in engineering evidence with its purpose and important result.
- Preserve the sequence `FAIL -> root cause -> fix -> retest -> PASS`; do not record only the final successful state.
- Record package filename and SHA-256 for every delivered ZIP.
- Record exact next action whenever Windows acceptance is pending.

## Data-safety rule

The authoritative application/core DB is:

`D:\timetable-intelligence-platform\services\api\data\timetable.db`

Before any installer/source migration/API restart/runtime QR test:

1. Resolve and verify the exact active DB path.
2. Read it without changing data and record integrity plus critical counts: sources, timetable entries, test records, changes, QR codes, QR scans and QR templates when present.
3. Create a consistent local/server backup before changing runtime/source.
4. Do not run destructive functional tests against production data; use isolated temporary/test databases.
5. Never select a database by changing the API working directory.
6. After restart, prove the same authoritative DB is active and critical counts are preserved.
7. A release is not accepted until Today Timetable, Weekly Timetable, Google Sheets, Sheet Updates, Test Monitor and QR work together against the same runtime/database.
8. On any mismatch, stop feature work and recover data/runtime first.

## GitHub continuity rule

GitHub is the source of truth for code and engineering continuity. The public repo must contain sanitized source, installer/recovery source, architecture/requirements, validation evidence, command/error/PASS history, deterministic build instructions and package hashes.

Private production databases and private Sheet/customer data are protected by verified local/server backups and are not committed to the public repo. GitHub must instead record the authoritative path, schema/count summaries, hashes where appropriate and safe recovery instructions.

A future chat must read, before changing runtime:

1. `docs/CURRENT_PROJECT_CONTEXT.md`
2. `docs/GITHUB_MANDATORY_HANDOFF_POLICY.md`
3. this file
4. the latest relevant `engineering-log/`
5. the latest release validation report

## Delivery-priority rule

Perform the minimum essential safety preflight, then build/test/deliver the working fix or release candidate. Update GitHub incrementally in the same turn. Do not delay code delivery for long documentation cleanup.

## QR Scale + Analytics v2 scope

- Smart compact QR management for lakhs of QR records.
- Server-side/index-backed search, filters, sort and pagination; no browser-side full-dataset loading.
- Prefer cursor/keyset pagination for very large QR/scan datasets.
- Compact table/card modes and on-demand detail panels instead of huge always-expanded QR cards.
- Every QR must retain immediate actions: Copy Source Link, Copy Public QR Link, Open/Show QR anytime, supported downloads, Analytics, Edit and existing lifecycle controls.
- Analytics must scale toward approximately 100 lakh / 10,000,000 accesses/scans using summarized/pre-aggregated data instead of full raw-event scans on each page load.
- Global analytics plus one-click per-QR drill-down.
- Raw/recent scan views must be server-paged/virtualized.
- QR redirect/content opening must remain fast and must not be blocked by analytics processing failure or backlog.
- Existing templates, bulk QR, styling, identity modes, verified-scan/anti-bot semantics, lifecycle behavior and shared-asset safety must not regress.
- SQLite may remain for local proof/dev; do not claim 10-million-access production readiness until the production design uses a server-grade scalable persistence/analytics architecture.
