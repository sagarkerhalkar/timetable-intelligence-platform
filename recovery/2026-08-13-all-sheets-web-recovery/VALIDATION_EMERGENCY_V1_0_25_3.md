# Emergency Recovery v1.0.25.3 validation

## Evidence from the real Windows recovery report

The previous recovery did not fail at the API layer. Its report showed:

- authoritative service/API DB sources: 4;
- newer/root DB sources: 8;
- the four trusted timetable sources were present;
- all four trusted source sync requests returned HTTP 200;
- Today API contained 12 timetable rows;
- Dashboard, Sheet Updates, Test Monitor and QR APIs returned HTTP 200.

However the screenshots after that recovery still showed:

- `Installed build: v1.0.11.1`;
- Google Sheets `0 of 0`;
- Today `0 classes`.

Therefore the previous acceptance test was insufficient: page HTTP 200 did not prove page content was using current API data, and the old `.next` production build had remained active.

## v1.0.25.3 correction

- Recover all source registrations from the newer/root DB, not only four trusted sources.
- Preserve core source IDs for existing workbooks.
- Insert missing source registrations without importing foreign timetable/content state from the root DB.
- Leave QR tables untouched.
- Pin the absolute authoritative database path.
- Sync four timetable sources first, then all additional enabled Sheets.
- Require Today API to contain rows.
- Apply known later cumulative web source for Today, Sheet Updates, Test Monitor/navigation.
- Remove the stale `.next` build.
- Run real `npm run typecheck` and `npm run build` on Windows before starting the web server.
- Final page checks cover Today, Weekly Timetable, Google Sheets, Sheet Updates, Test Monitor and My QR Codes.

## Local validation

- Python helper compilation: PASS.
- Synthetic source-registry test: 4 core + 8 newer -> 8 authoritative source rows: PASS.
- Existing core source IDs preserved: PASS.
- QR table remained unchanged in the synthetic merge: PASS.
- PowerShell delimiter count audit: PASS.
- PowerShell unsafe variable-colon audit: PASS except normal `$env:` syntax.
- Protected port 3457 guard retained.

## Authoritative boundary

The real Windows run is still authoritative because live Google Sheet downloads, the installed Node dependency tree, the current source tree and real databases exist only on the user's server.