# v1.0.25 implementation map

This file explains the focused UI changes so a new chat/developer can locate the implementation quickly.

## Shared page system

- `apps/web/lib/pagination.ts`: page count, clamping, slicing, compact page-number window.
- `apps/web/lib/pagination.test.ts`: permanent pagination regression tests.
- `apps/web/components/pagination-controls.tsx`: shared First / Previous / numeric / Next / Last controls plus item-range summary.

## My QR Codes

Runtime file: `apps/web/app/qr/codes/page.tsx`.

Contract:
- fixed 8 QR campaigns/page;
- larger responsive QR cards instead of the old compact table;
- real QR PNG preview on each card;
- `Show QR` large modal;
- source/destination link visible and `Copy Source Link` action;
- tracked public QR link and `Copy QR Link` action;
- clipboard uses `navigator.clipboard` with textarea/`execCommand` fallback for LAN/older browsers;
- checkboxes persist selection across pages;
- `Select this page`, `Clear selection`, and `Delete Selected (n)`;
- multi-delete intentionally reuses the existing individual DELETE route in bounded groups so the established shared-logo/background reference safety remains authoritative;
- existing Analytics, Edit, PNG/SVG/PDF, active/inactive, clear-scan and channel-specific QR behavior is preserved.

## Templates

Runtime file: `apps/web/app/qr/templates/page.tsx`.

Contract: search + 6 templates/page. Template create/edit/duplicate/default/delete behavior is unchanged.

## Bulk Create

Runtime file: `apps/web/app/qr/bulk/page.tsx`.

Contract:
- 6 templates/page;
- 10 Name + URL input rows/page while preserving absolute row indexes;
- 10 generated QR results/page;
- result cards expose QR preview, Copy URL, PNG and per-QR Analytics;
- existing typed `parseBulkQrRows` helper remains the parsing authority.

## Statistics

Runtime file: `apps/web/app/qr/stats/page.tsx`.

Contract:
- Device Intelligence: 6 device cards/page;
- Recent verified scan history: 15 rows/page;
- analytics calculations/identity semantics are unchanged.

## Styling

Runtime file: `apps/web/app/globals.css`, section marked `v1.0.25`.

Adds responsive large QR card layout, pagination controls, selection bar, QR preview modal and mobile rules.

## Release validation

Every changed TypeScript page/component is checked semantically using `strict: true` plus `noUncheckedIndexedAccess: true` before packaging. The Windows installer remains authoritative and still runs the complete backend suite, Vitest suite, real project `tsc --noEmit`, full Next.js build and runtime acceptance gates before keeping the update.
