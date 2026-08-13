# v1.0.25 Validation Report

## Local/source validation completed

- Shared pagination utility semantic TypeScript check with `strict=true`: PASS.
- Shared pagination utility semantic TypeScript check with `noUncheckedIndexedAccess=true`: PASS.
- Pagination runtime contract (page count, clamping, slices, numeric window): PASS.
- Changed QR pages semantic TypeScript check with `strict=true` + `noUncheckedIndexedAccess=true`: PASS.
- Checked pages: My QR Codes, Templates, Bulk Create, Statistics, shared PaginationControls, qr-bulk parser.
- Clipboard fallback code is included for LAN browsers without `navigator.clipboard`.
- My QR Codes source contains large QR preview, Copy Source Link / Copy QR Link, checkbox selection and Delete Selected.
- Existing backend QR delete route is reused for multi-delete; no new destructive API contract added.

## Page-size contract

- QR Library: 8/page.
- Templates: 6/page.
- Bulk template chooser: 6/page.
- Bulk input rows: 10/page.
- Bulk results: 10/page.
- Device Intelligence: 6/page.
- Recent verified scans: 15/page.

## Not claimed locally

This environment is not the user's complete Windows runtime tree with the installed Next.js dependency set and databases. Therefore v1.0.25 is not called Windows-proven until `RUN_V1_0_25_NOW.cmd` completes the real installer without rollback.
