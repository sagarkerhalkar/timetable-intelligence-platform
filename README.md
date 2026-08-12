# Timetable Intelligence Platform

Google Sheets-driven timetable, content search, sheet-update tracking, Test Monitor, notifications, and QR Studio for a Windows LAN server.

## Stable vs release candidate

- Stable working branch: `v1`
- Current release candidate: `v1.0.24-qr-templates-bulk-analytics`
- Do **not** treat the release-candidate branch as production until its Windows installer completes the full regression/typecheck/build/runtime gate without rollback.

## v1.0.24 QR Studio release candidate

This branch documents and carries the v1.0.24 QR Templates + Bulk Creation + Per-QR Analytics change set.

Main QR workflow:

`New QR -> Templates -> Bulk Create -> My QR Codes -> Analytics`

v1.0.24 adds:

- multiple server-side reusable QR templates;
- template design reuse: logo, full-screen image, colors, dots/markers, frame, scan screen, animation, tracking and identity settings;
- Bulk Create using only `Name + URL` rows after choosing a template;
- manual rows, pasted spreadsheet/CSV data, and CSV/TXT upload;
- up to 500 QRs per request;
- independent ID, slug, destination and analytics for every generated QR;
- per-QR analytics links from Bulk results and My QR Codes;
- template provenance without coupling old QRs to future template edits;
- template deletion preserves already-created QR campaigns;
- shared uploaded assets remain protected while referenced by another QR/template.

## Architecture and continuation docs

Read these first in a new chat or development session:

1. `docs/CURRENT_PROJECT_CONTEXT.md`
2. `docs/QR_PLATFORM_ARCHITECTURE.md`
3. `docs/V1_0_24_QR_TEMPLATES_BULK_ANALYTICS.md`
4. `reports/VALIDATION_V1_0_24.md`
5. `release-source/v1.0.24/README.md`

The public repository intentionally excludes databases, credentials, recipient data, private Sheet contents, runtime logs, cookies/tokens and uploaded customer assets.
