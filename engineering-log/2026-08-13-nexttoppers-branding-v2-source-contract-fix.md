# 2026-08-13 — NextToppers branding/performance V2 source-contract fix

## Windows FAIL
The first `NEXTTOPPERS_QR_BRANDING_PERFORMANCE` patch stopped safely with:

`Expected source contract not found in D:\timetable-intelligence-platform\apps\web\app\qr\page.tsx`

It had already backed up web source and reported the QR navigation as already patched. It did not modify the production database, did not restart API 3550, and did not touch protected port 3457.

## Root cause
The first branding patch depended on one exact older source string in `app/qr/page.tsx`. The current working runtime source is newer/different, so the exact-string guard rejected a valid source state.

## Fix
V2 no longer requires that exact QR Builder string. It:
- patches known NextToppers branding only when present;
- treats already-patched/newer source as acceptable instead of failing;
- preserves the real tracked QR URL for Copy/Open actions;
- hides the raw public hostname only from the known normal My QR Codes display label when that markup exists;
- creates QR metadata/manifest only when absent and preserves existing layout/manifest files;
- runs Vitest and `npm run build` before stopping web 3500;
- switches only web 3500 to Next.js production mode after validation;
- leaves SQLite, API 3550 and port 3457 untouched.

## Corrected user package
`NEXTTOPPERS_QR_BRANDING_PERFORMANCE_V2.zip`

SHA-256:
`c0e15c6ffddcc27c9a6bbb20e72324c21c11e7d9e3d658c305c57807b664f495`

## Acceptance
Package generation/ZIP integrity: PASS.
Real Windows acceptance: PENDING.

Run: `RUN_NEXTTOPPERS_QR_V2.cmd`.
