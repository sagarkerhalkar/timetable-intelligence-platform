# Timetable Intelligence Platform — Current Project Context

## Purpose
Windows/LAN application that reads trusted Google Sheets for timetable/content/test intelligence and includes a commercial QR Studio.

## Sheet sources
1. Prarambh Humanities 11/12
2. Prarambh Science 11/12
3. Master Commerce 11/12
4. Nirmaan Class 8

Parser rules:
- Humanities/Science/Commerce: Weekly Planner + Time Table related tabs.
- Nirmaan: Weekly Planner only.
- Parsing must be resilient to row/column movement.

## Runtime
- Windows target: `D:\timetable-intelligence-platform`
- Web: 3500
- API: 3550
- Public QR host: `https://nexttoppers.sagarkerhalkar.com`
- Port 3457 is protected and must not be touched.

### CRITICAL database rule after 2026-08-13 incident

The authoritative application/core SQLite DB is:

`D:\timetable-intelligence-platform\services\api\data\timetable.db`

`DATABASE_URL` historically defaults to the relative value `sqlite:///./data/timetable.db`, so changing Uvicorn's working directory can silently switch the entire application to another DB. A recovery from another chat started Uvicorn from the project root, making `D:\timetable-intelligence-platform\data\timetable.db` active. That made recovered QR records visible but bypassed/diverged from the timetable/Google Sheet core DB.

Permanent rule:
- never recover QR by running the whole API against the root `data\timetable.db`;
- if QR data exists in another DB, merge only `qr_templates`, `qr_codes`, `qr_scans` and missing `qr_assets` into the authoritative service/API DB;
- never replace timetable/source/change/test/content/notification core tables from a QR recovery DB;
- pin `DATABASE_URL` to the absolute service/API DB path during recovery so a different working directory cannot switch databases again.

See `docs/INCIDENT_2026_08_13_DATABASE_WORKDIR_RECOVERY.md` and `recovery/2026-08-13-core-db-repair/`.

## Important timetable logic
- India civil Monday–Sunday week boundaries; never use UTC weekday math for India civil dates.
- Today cards open exact date + stream.
- Test Monitor Mon–Sat Test Date maps to that week's Sunday for current-week readiness; original date remains visible.
- Sheet Updates default to human grouped stories; technical cell audit is secondary.

## QR locked requirements through v1.0.24
- 7 QR types: Calendar, Contact, Email, Geo, Phone, URL, Wi-Fi.
- Advanced QR styling: dots, marker border, marker center, colors, frame, logo sizing.
- Branded scan screen: animated brand/logo/full-page image, image/logo sizing.
- Anonymous and Identify-with-Email modes.
- Maximum legitimate anonymous device/browser telemetry where exposed.
- Verified scan counting; preview bots do not inflate people metrics.
- Unique browser/device is not falsely described as unique human person.
- Channel/source attribution: Exact / Detected / Unknown.
- My QR Codes lifecycle: active/inactive, edit, downloads, clear scans, delete.
- Multiple server-side reusable QR templates.
- Bulk URL QR generation from one template using only Name + URL.
- Every bulk-generated QR has independent analytics.
- Template deletion must not delete existing generated QR codes.
- Template/shared image assets must not be removed while another QR/template still references them.

## QR scale requirement — next major release

The current QR list is too bulky and the Analytics page is too small/simple for the intended production scale.

Locked target scale:
- support lakhs of QR codes without endless pages or browser-side loading of the full dataset;
- support approximately 100 lakh / 10,000,000 QR accesses/scans and the resulting analytics data;
- all QR list/search/filter/sort/pagination must be server-side and index-backed;
- prefer cursor/keyset pagination for very large QR and scan datasets; do not use deep client-side pagination over all records;
- My QR Codes default view must be compact and information-dense, with optional card/table modes and on-demand detail drawers/modals instead of huge always-expanded cards;
- provide fast search by QR name, slug/link, type, status, template, date range and relevant tags/metadata;
- bulk selection must work across filtered result sets without loading every QR into the browser;
- Analytics must become a full dashboard rather than a small page: global totals, verified scans, unique devices/browsers without falsely calling them unique humans, trend charts, top QR codes, top source/channel, countries/regions, device/browser/OS, time/date filters, comparison periods and per-QR drill-down;
- recent/raw scan tables must use server-side pagination/virtualization and never render millions of events at once;
- heavy analytics must use pre-aggregated/summary data and asynchronous/background aggregation rather than scanning all raw events on every page load;
- data retention/archival strategy must be configurable so long-term raw analytics can scale without making the live UI slow;
- exports of large analytics/QR result sets should be generated asynchronously rather than blocking the UI;
- QR redirect/scan path must stay fast even when analytics storage is under heavy load;
- the QR scan endpoint must fail safely: analytics processing must never delay or break the actual redirect/content experience;
- architecture must be designed for horizontal growth beyond the current local SQLite proof/runtime. SQLite may remain for local proof/dev, but the production scale design must allow a server-grade database/analytics store before claiming readiness for 10 million accesses;
- no regression to existing QR identity, verified-scan, anti-bot, template, bulk, analytics, design, lifecycle or shared-asset protections.

## Release history lesson
Do not weaken tests to make a release pass. When display/API contracts change, update all cumulative regressions. Windows runtime validation is authoritative; local/static checks are not enough to claim release success.

## GitHub policy
Repository: `sagarkerhalkar/timetable-intelligence-platform`
Stable source branch: `v1`.
Public repository must never contain databases, credentials, recipient lists, private Sheet data, runtime logs, cookies or tokens.
Release candidates should go to a separate branch/PR until Windows acceptance succeeds.

### Mandatory engineering handoff

`docs/GITHUB_MANDATORY_HANDOFF_POLICY.md` is mandatory for every future development session.

Before a development session is considered complete, GitHub must contain the engineering-relevant requirements, decisions, changed source, validation commands/results, every meaningful FAIL, root cause, fix, PASS evidence, package/checksum state, Windows installer/rollback status, unresolved blockers and exact next action. Chronological evidence goes under `engineering-log/`.

A future chat/developer must be able to continue from GitHub without depending on an inaccessible prior chat. Sensitive/private data remain excluded because the repository is public.

The 2026-08-13 handoff-repair evidence is recorded in:
- `engineering-log/2026-08-13-v1.0.25-handoff-and-runtime-recovery.md`
- `docs/INCIDENT_2026_08_13_DATABASE_WORKDIR_RECOVERY.md`

## GitHub v1.0.24 handoff

- Repository: `sagarkerhalkar/timetable-intelligence-platform`
- Stable branch: `v1`
- Release-candidate branch: `v1.0.24-qr-templates-bulk-analytics`
- Draft PR: `#12`
- Do not merge the release candidate until the real Windows installer completes all gates without rollback.
- The public branch contains sanitized continuation docs plus actual v1.0.24 Templates/Bulk frontend source and the independent-per-QR analytics regression test.

## v1.0.24.1 strict TypeScript correction

The first v1.0.24 Windows run proved 105/105 backend tests and 16/16 web tests, then stopped at four TS2532 errors in the new Bulk Generator parser because the repository uses `strict` + `noUncheckedIndexedAccess`. v1.0.24.1 moves bulk parsing to `apps/web/lib/qr-bulk.ts`, adds `qr-bulk.test.ts`, and requires strict semantic TypeScript validation before packaging. No v1.0.24 product feature was removed or changed.

## v1.0.25 UI policy

The QR product now follows the same no-endless-page rule used elsewhere. My QR Codes, Templates, Bulk input/results, Device Intelligence and Recent Scan History use a shared page system. My QR Codes uses large responsive cards with actual QR previews, Copy Source Link, Copy QR Link, Show QR, checkbox multi-select and Delete Selected. Multi-delete reuses the existing QR delete endpoint so shared template/logo/background asset reference protection remains unchanged.

## Current recovery state — 2026-08-13

Do not install another QR/UI release yet. First restore the authoritative service/API DB runtime, merge QR-only data from the root DB, force-sync the four trusted timetable Sheets, and prove Today/Weekly/Test Monitor/Sheet Updates/QR together. Only after that should PR #12 or any later release be considered for Windows acceptance.