# v1.0.11.1 TypeScript build repair

## Failure reproduced

The Windows installer successfully installed the v1.0.11 Python package and completed 69 backend tests, but `npm run typecheck` failed in `apps/web/app/changes/page.tsx`.

The project uses both `strict` and `noUncheckedIndexedAccess`. Under those settings, `match[1]` and `match[2]` from a regular-expression result have type `string | undefined`, even after checking that the match object exists.

Reported diagnostics:

- TS2322: `string | undefined` was not assignable to `string`.
- TS2532: capture-group access was possibly `undefined`.

## Correction

`cellParts()` now stores both capture groups using nullish fallback values, validates that both are non-empty, and only then builds the uppercase column and full cell address. Strict settings stay enabled and no unsafe cast is used.

## Validation

- Backend: 69 tests passed.
- Python application compilation passed.
- Dedicated TypeScript fixture with `strict` and `noUncheckedIndexedAccess` passed.
- Full web source strict check with local framework declaration stubs passed.
- 41 TypeScript/TSX files transpiled with zero syntax diagnostics.
- PowerShell scripts have balanced delimiters and no unsafe `$variable:` interpolation.
- ZIP integrity passed.

The actual Windows installer continues to run the real `npm run typecheck` and complete `npm run build` using the installed Next.js/React dependency tree. Failure restores the previous code, database and `.next` build.

## Release artifact

- Package: `timetable-intelligence-platform-v1.0.11.1-typescript-build-fix.zip`
- SHA-256: `356a32b55d8ada232032ab355261f712f0f4c83e3d251f531914a94391e694ee`
- Protected port: 3457
- LAN web address: `http://156.156.40.51:3500`
