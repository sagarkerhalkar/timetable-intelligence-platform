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
