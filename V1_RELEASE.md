# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.11.1-typescript-build-fix.zip`

SHA-256: `356a32b55d8ada232032ab355261f712f0f4c83e3d251f531914a94391e694ee`

## v1.0.11.1 strict TypeScript build repair

- Reapplies the complete v1.0.11 responsive background sync, reliable Search, Google Sheet manager, weekly Sunday Test Operations, notification guidance and Excel-style Sheet Updates update after the v1.0.11 Windows build rolled back.
- Fixes the exact `app/changes/page.tsx` errors TS2322 and TS2532. The project enables `strict` and `noUncheckedIndexedAccess`, so regular-expression capture groups are checked before Row, Column and Cell values are created.
- Strict TypeScript settings remain enabled; the repair does not use unsafe casts or disable compiler checks.
- Automated validation: 69 backend tests passed, Python compilation passed, strict `noUncheckedIndexedAccess` regression passed, all 41 TypeScript/TSX files transpiled without syntax diagnostics, full source strict check with local framework declarations passed, PowerShell structure/interpolation checks passed, and ZIP integrity passed.
- The Windows installer still runs the real installed dependency tree through `npm run typecheck` and the complete Next.js production build before reporting success. Any failure restores the previous code, database and `.next` build.
- The application reports build `v1.0.11.1`; the npm package uses the valid SemVer value `1.0.11-patch.1`.
- Existing database, connected Google Sheets, notification rules and isolated ports remain preserved. Port 3457 remains protected.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes databases, credentials, recipients, logs, runtime files and backups.
