# v1.0.25 — Paged UX + Larger QR Library

## Scope

This release is intentionally UI-focused. Existing QR tracking, templates, bulk creation, Wi-Fi behavior, scanner identity and analytics semantics are not changed.

## App-wide page-system policy

Long collections must not become endless pages. Existing Content and Sheet Updates paging remains unchanged. v1.0.25 extends the same policy to the QR product:

- My QR Codes: 8 large QR cards per page.
- QR Templates: 6 templates per page.
- Bulk Create template chooser: 6 templates per page.
- Bulk Create input table: 10 Name + URL rows per page.
- Bulk Create result list: 10 generated QRs per page.
- Device Intelligence: 6 device summaries per page.
- Recent verified scan history: 15 rows per page.

The shared `PaginationControls` component and `pagination.ts` utility are used instead of separate ad-hoc paging implementations.

## My QR Codes redesign

Each QR is now a larger responsive card containing:

- real QR preview;
- Show QR large-preview action;
- QR name/type/tracking/identity/template;
- Active/Inactive state;
- verified scans, unique devices, countries and created date;
- source/destination link with Copy;
- tracked public QR link with Copy;
- Analytics, Edit, Show QR and PNG actions;
- existing Download SVG/PDF, channel QR, activate/deactivate, clear data and permanent delete actions.

## Multi-select delete

QR cards have checkboxes. The user can select several QRs across pages and use `Delete Selected`.

Deletion intentionally reuses the existing one-QR DELETE contract in bounded groups instead of introducing a second destructive backend pathway. This preserves the existing shared-logo/background reference-safety behavior.

## Clipboard compatibility

Copy Source Link and Copy QR Link use `navigator.clipboard` when available. A textarea + browser copy fallback remains for LAN/older browser environments where the modern Clipboard API is unavailable.

## Release safety

No new QR analytics semantics are introduced in this release. The Windows installer still performs the complete backend suite, web regressions, strict TypeScript, Next.js production build, browser/mobile page smoke checks, QR lifecycle, templates/bulk/per-QR analytics and timetable/Test Monitor/Sheet Updates gates before accepting the update.
