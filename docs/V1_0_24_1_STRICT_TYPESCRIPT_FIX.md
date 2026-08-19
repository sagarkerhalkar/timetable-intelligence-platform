# v1.0.24.1 — Bulk Generator strict TypeScript correction

## Windows failure

The first v1.0.24 Windows acceptance run passed:

- 105/105 backend tests;
- 16/16 web regression tests.

It then failed `npm run typecheck` in `apps/web/app/qr/bulk/page.tsx` with four TS2532 diagnostics.

## Root cause

The project enables TypeScript `strict` mode and `noUncheckedIndexedAccess`. Under those rules, indexed values remain possibly undefined unless handled explicitly. The failing values were:

- `tab[0]`
- `comma[0]`
- `match[1]`
- `match[2]`

The v1.0.24 pre-package validation only performed a weaker transpile/syntax check on the new frontend source. That can pass while the real project `tsc --noEmit` gate still fails.

## Correction

Bulk row parsing now lives in a typed `qr-bulk.ts` helper and uses explicit nullish fallbacks before indexed values are trimmed/used. The Bulk page imports that helper instead of embedding a compressed parser.

Permanent parser tests cover:

- Excel / Google Sheets tab-separated paste;
- CSV paste;
- `Name https://...` paste;
- malformed input kept visible for UI validation.

## Release-process rule

For every new or changed TypeScript feature, pre-package validation must use semantic TypeScript with both:

- `strict: true`
- `noUncheckedIndexedAccess: true`

A transpile-only result is not sufficient release evidence.

No QR template, bulk analytics, Wi-Fi, identity, Device Intelligence, timetable, Test Monitor or Sheet Updates product behavior changed in v1.0.24.1.
