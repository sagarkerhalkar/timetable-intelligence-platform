# Timetable Intelligence Platform

Google Sheets-driven timetable, content search, sheet-update tracking, Test Monitor, notifications, and QR Studio for a Windows LAN server.

## Stable vs release candidate

- Stable working branch: `v1`
- Current release-candidate branch: `v1.0.24-qr-templates-bulk-analytics`
- Current package correction: **v1.0.24.1 strict TypeScript fix**
- Do **not** treat the release-candidate branch as production until its Windows installer completes the full regression/typecheck/build/runtime gate without rollback.

## QR Studio release candidate

Main QR workflow:

`New QR -> Templates -> Bulk Create -> My QR Codes -> Analytics`

The v1.0.24 feature set adds:

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

## v1.0.24.1 correction

The first real Windows v1.0.24 run passed **105/105 backend tests** and **16/16 web regression tests**, then `tsc --noEmit` found four TS2532 errors in the new Bulk Generator parser. The project uses both `strict` and `noUncheckedIndexedAccess`, while the pre-package check had only done a weaker transpile/syntax validation.

v1.0.24.1 moves row parsing into a typed `qr-bulk.ts` helper, uses explicit nullish fallbacks for indexed values, and adds permanent parser regression tests. Future TypeScript release checks must use semantic strict TypeScript with `noUncheckedIndexedAccess` before packaging.

## Architecture and continuation docs

Read these first in a new chat or development session:

1. `docs/CURRENT_PROJECT_CONTEXT.md`
2. `docs/QR_PLATFORM_ARCHITECTURE.md`
3. `docs/V1_0_24_QR_TEMPLATES_BULK_ANALYTICS.md`
4. `docs/V1_0_24_1_STRICT_TYPESCRIPT_FIX.md`
5. `reports/VALIDATION_V1_0_24_1.md`
6. `release-source/v1.0.24.1/README.md`

The public repository intentionally excludes databases, credentials, recipient data, private Sheet contents, runtime logs, cookies/tokens and uploaded customer assets.
