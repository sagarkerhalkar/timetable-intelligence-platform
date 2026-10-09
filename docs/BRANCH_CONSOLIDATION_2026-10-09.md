# GitHub branch consolidation audit — 2026-10-09

## User request

Use ONE understandable GitHub branch, with an easy README and reliable Windows/Linux installation. Protect the worldwide live QR service, permanent printed QR slugs, destinations, historical scans, Cloudflare Worker/KV, Google Sheets and timetables.

## Findings from the GitHub connector (read-only branch comparisons)

- Repo: sagarkerhalkar/timetable-intelligence-platform (public).
- GitHub default branch: main.
- At inspection: 22 branch refs; main held only a short README, not the deployed full app.
- nexttoppersqr has QR release snapshots, worker/API fragments and engineering/recovery notes, but is **not proven identical** to the active Windows application at D:\timetable-intelligence-platform.
- Release candidate feature/qr-geo-device-store-analytics-20261009 contains isolated read-only reporting; PR #16 is draft and NOT production-approved.
- An additional feature/qr-geo-device-store-reporting-20261009 branch contains separate API/dashboard/store reporting experiments; NOT production-approved.
- Separate full-app Linux installation is unverified. Do NOT mark the application Linux-ready.

### Branches reachable from nexttoppersqr already (behind: no separate new commits compared to nexttoppersqr)

- commerce-fix-rc
- production-working
- v1
- v1.0.24-qr-templates-bulk-analytics
- v1.0.26-qr-scale-analytics-v2
- working-current

### Divergent branches — must inspect and preserve their distinct commits

- agent/v1.0.13-fast-navigation
- agent/v1.0.14-performance-cache
- agent/v1.0.14.1-pagination-contract-fix
- agent/v1.0.15-stability-week-boundary
- agent/v1.0.15.1-stable-test-gate-fix
- agent/v1.0.15.2-release-gate-fix
- agent/v1.0.16-qr-analytics
- agent/v1.0.17-short-qr-neutral-link
- agent/v1.0.18-qr-studio-analytics
- agent/v1.0.19-commercial-qr-builder
- agent/v1.0.20-international-qr-platform
- v1.0.27-worker-gateway-public-qr

### Newer candidate branches (ahead of nexttoppersqr)

- feature/qr-geo-device-store-analytics-20261009
- feature/qr-geo-device-store-reporting-20261009

Important: an ancestor branch may be redundant as a pointer, but is never proof its release was tested. A diverged branch may contain an important fix, conflicting legacy behavior, or both. Never merge all branches automatically.

## What was done safely this session

- Added tools/qr-insights/qr_insights.py to main, copied from the isolated reporting candidate (reporting only; no Worker/backend edits).
- Added tools/qr-insights/safe_snapshot.py to main (read-only SQLite backup helper). A sample-database test confirmed independent, integrity-checked backup with source count unchanged.
- Replaced the insufficient main README with step-by-step Windows and Linux instructions for the standalone report tools.
- Existing production and historical branch refs left unchanged, including working-current and production-working.
- No API/web/Worker restart, KV write, database migration, QR image change, or production install occurred.

## Exact blockers to a truthful 'main = complete working app'

1. Need a sanitized, complete copy of the *currently running* Windows server source (API, frontend, package/lock files, schemas/migrations, installers, configs/examples, tests, build scripts). Do not commit production .env, secrets or databases.
2. Confirm real API process, deployed bundle, Worker version, Cloudflare edge/KV mapping and the authoritative active DATABASE_URL. There was a historical split between service/API timetable.db and project-root data/timetable.db.
3. Collect critical row-count and QR redirect baseline with a separate consistent DB backup and archive source hashes. Do not alter live data to compare.
4. Review distinct commits in each divergent branch and port only validated, applicable changes onto a complete staging source.
5. Produce an offline deterministic Windows installer/update and Linux full-app installation, with explicit prerequisites, start/stop/status/backup/restore instructions.
6. Pass backend tests, strict TypeScript build, actual Windows and Linux staging smoke tests, QR redirect performance, per-QR scan counts, timetable sources, weekly/today/test monitoring, PDF/CSV reports and rollback.
7. Only after release acceptance: bring main to the approved complete source, record tag(s)/immutable refs for unique history, verify it can clone/build cleanly and restore to a staging environment; then reduce obsolete branches. Do not delete divergent history without replacement.

## Current release state

**STATUS: SAFE PARTIAL CONSOLIDATION ONLY.** Main is becoming the single documented entrypoint and contains isolated tools. It is **not yet the canonical runnable production application**. PR #16 is draft. No production deployment is authorized from this repository state.

## Next local commands (read-only diagnostics)

Windows PowerShell:

~~~powershell
cd D:\timetable-intelligence-platform
git status --short
git remote -v
git branch --show-current
Test-Path "D:\timetable-intelligence-platform\services\api\data\timetable.db"
Get-NetTCPConnection -LocalPort 3550 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess
~~~

If not a Git checkout, git status will fail; this is informational only. Do not git init, git reset, git clean, git checkout, force-push or overwrite the live folder to silence an error.

For report-only download, follow main README. For complete app update, use an isolated staging copy and a verified production backup.

## Safe project invariants

- Existing printed QR slugs/images, destination links, active status, QR user IDs, visitor hashes and historic scan records remain unchanged.
- Do not deploy or rebuild Cloudflare Worker/KV for an analytics-only upgrade.
- Do not change existing timetable, Google Sheet, notification and test-series logic to add QR reports.
- Maintain auth/admin boundaries; never expose raw scan PII publicly.
- QR confirmed scan count is **not** app downloads. District is Unknown when not provided by trusted geo data.
- Historical branches remain until all unique validated work is represented in main and a lossless recovery point exists.


## Live Windows machine diagnostic supplied 2026-10-09 (direct user-provided PowerShell result)

On the actual server, the user ran:
- cd D:\timetable-intelligence-platform — succeeded
- git status --short, git remote -v, git branch --show-current — all failed with "fatal: not a git repository (or any of the parent directories): .git"
- Test-Path "D:\timetable-intelligence-platform\services\api\data\timetable.db" — True
- Get-NetTCPConnection -LocalPort 3550 -State Listen — found 0.0.0.0:3550 LISTEN

Interpretation:
1. The live application directory has no Git metadata, so a normal Git pull in that directory CANNOT update it.
2. The expected SQLite database exists, but that fact does not confirm the live API is using it.
3. The API listener exists, but service health, live process startup path and source revision are not yet verified.
4. DO NOT run git init/clone/reset/checkout/pull or release ZIP in the live directory to silence the error. Do not publish the live application directory unreviewed to this public repository.
5. Next minimal read-only diagnostic: identify the process bound to 3550, check GET /api/v1/health, inspect source directory structure, confirm active DB configuration privately without exposing credentials.
6. Then assemble a sanitized complete source tree and isolated staging build for a true main-branch release; existing QR Worker/KV and protected 3457 must stay unchanged.


## Second live Windows diagnostic (confirmed from user, 9 October 2026)

- API port 3550 PID 21028, executable C:\Users\Pc\AppData\Local\Python\pythoncore-3.14-64\python.exe; listener 0.0.0.0.
- GET http://127.0.0.1:3550/api/v1/health returned status=ok, service=Timetable Intelligence API, version=1.0.24.1, environment=production, timestamp=2026-10-09T08:45:27.056079+00:00.
- Web port 3500 listening at 0.0.0.0 PID 19064.
- Windows app is a non-Git runtime tree with services/api/app, services/api/tests, pyproject.toml, apps/web/app, apps/web/components, apps/web/lib, package.json, package-lock.json, .next, node_modules. Has local .github, github-source, payload, .wrangler, recovery folders and many backups.
- Existing authoritative candidate DB file in services/api/data exists but the API connection's DATABASE_URL has NOT been established (no file disclosure).
- These facts prove a live app is listening and its two source trees exist, not that the root app is safe for git pull or that running source equals the historical version string.
- Added tools/local-source-audit/prepare_source_review.py to main. It ONLY reads an explicit whitelist of source-code paths, excludes common sensitive/runtime files and suspicious secret patterns, and creates a separate offline ZIP with a manifest. It does not deploy or upload. **Automated secret filtering is not a guarantee. Review archive before private upload or any public commit.**
- Next required input: protected source-only archive privately provided for code reconciliation; compare actual source with nexttoppersqr and all divergent commits, run tests/staging; then replace main with verified whole working source and archive old branches/tags. No production changes until gates pass.


## 2026-10-09 actual-source QR analytics feature patch

The user uploaded a sanitized source archive from the running (non-Git) Windows installation, named NextToppers-Working-Source-Review-20261009-142102.zip. The archive held services/api/app/{main.py,api/qr_fast.py,api/qr_scale.py,api/routes.py,database.py}, apps/web/app/qr/stats/page.tsx, qr-product-nav.tsx, web lockfiles and tests. Source inspection confirmed version 1.0.24.1, API 3550/web 3500, and a QR fast scan path already persisting country/device/browser/OS plus region/city edge telemetry.

**Delivered tested local source patch ZIP:** NextToppers_QR_Analytics_Working_Source_Patch_FLAT_2026-10-09.zip

SHA256: be4f8631d549d72387c693d3c2fb97b043f90fdfc404b37cb62b91a4bd9bb1f0

This ZIP was generated as a conversation download artifact; it is NOT on GitHub yet. Do not claim GitHub main includes this feature source or claim production has been modified.

Additive patch:
- NEW services/api/app/api/qr_reports.py: /api/v1/qr-reports/{summary,export.csv,export.pdf}, verified non-bot event aggregation, country/state/city/district (unknown where missing), anonymized per-browser/QR scan counts and device types, Play/App Store QR traffic separate from installs.
- NEW apps/web/app/qr/reports/{page.tsx,reports.css}: Geo + Stores dashboard with QR selector/period filter and CSV/PDF exports.
- NEW services/api/scripts/import_store_metrics.py: explicit, locally verified normalized publisher figures to a separate SQLite database. No QR-specific installs inferred from clicks.
- Additive edits applied by INSTALL_WINDOWS.py to services/api/app/main.py, apps/web/components/qr-product-nav.tsx, apps/web/app/qr/stats/page.tsx.
- ROLLBACK_WINDOWS.py restores original source files if unchanged by others. Both scripts are in the packaged ZIP.

Tests:
- 3/3 FastAPI backend synthetic tests passed (counts, geo Unknown, anonymous repeat browser clicks, PDF/CSV, separate store metric DB).
- TSX syntactic transpilation: 0 errors; full Next strict typecheck/build NOT run (project node_modules not in uploaded ZIP).
- Source installer dry-run, apply with separate synthetic DB + SQLite consistent backup, and rollback passed on isolated uploaded-source copies.
- Sample PDF rendered and visually inspected; ZIP passed unzip integrity check.
- Real production install, process restart and full acceptance: NOT PERFORMED.

**Next immediate action:** User privately downloads the released patch, first runs dry-run on the working Windows source, verifies exact active DATABASE_URL (historical two-DB incident), then runs --apply only after confirming active DB. A controlled staged Next build + API/web restart is still necessary to make the new screen appear. Test all old QR redirect URLs and timetable functionality before marking accepted. No Cloudflare Worker/KV deployment needed.

Branch consolidation remains blocked until sanitized live source is reconciled and production acceptance passes. No branches were deleted/merged in this patch session.


## 2026-10-09 15:36 IST — compact QR Insights for MAIN web application (source ZIP delivered)

User requested improvement of working report page: current standalone page is too lengthy, wants a new tab within original NextToppers main web app, and City and District should not be repeated separately when they are the same location name.

**Delivered candidate:** `NextToppers_QR_Compact_Main_Web_Update_2026-10-09.zip` (conversation artifact only, not committed as runtime source).
**SHA-256:** `d20848e97f40138c47b309e8c58134a84e902cd271bfc2e7f4fb6e6d6fa5f3b9`
**ZIP entries:** 13, ZIP integrity test PASS.
**Source-based Python tests:** 4/4 PASS using synthetic 50-QR/1,615-scan SQLite.
**Frontend validation:** TypeScript TSX transpilation diagnostics 0; full Next.js strict typecheck and production build cannot run in this sandbox because Next/React dependencies are not installed (npm registry unavailable). Mandatory user-host staging gate in shipped script.
**Live deployment:** NOT performed in this session.

Files in candidate:
- `apps/web/app/qr/reports/page.tsx` and `reports.css` replace the previous long page with professional compact tabs Locations / Devices / App Stores, 12-row paging, mobile-responsive cards, period/QR search, PDF/CSV downloads.
- City/District combined **in the UI**; show one label if same. When district unavailable, do not claim city is a verified district.
- `INSTALL_COMPACT_MAIN.py`: additive main-sidebar nav and QR product nav integration; refuses mismatch between API QR count and the selected root 50-QR DB. Consistent backup of root DB and source before any edits. No API/Worker/QR redirect edits.
- `PREPARE_AND_ACTIVATE.ps1`: staging strict TypeScript and Next.js build, protected initial DB snapshot. `-GoLive` is explicit opt-in, checks known Uvicorn/Node processes and aborts on Windows-service-managed launcher. Restart API/web only under these guards. Retains previous .next for attempted rollback. **Not exercised on real Windows host.**
- `1_INSTALL_SOURCE.cmd`, `2_BUILD_SAFELY.cmd`, `3_ACTIVATE_MAIN_APP.cmd`, `ROLLBACK_COMPACT_MAIN.py`, beginner `README_FIRST.txt` and synthetic tests.

**Important live database:** `D:\timetable-intelligence-platform\data\timetable.db` (50 QR codes, 1615 raw scans as user verified earlier). Smaller service/api/data DB (23 QRs, 4 scans) MUST NOT be selected during activation. Live dashboard previously displayed 1209 verified scans. The installer checks **current** live API QR count each run and refuses mismatch.

Main page expected after successful physical Windows cutover: `http://156.156.40.51:3500/qr/reports`. Sidebar tab `Geo & Store Analytics` sits immediately after `QR Analytics`; QR product menu includes `Geo & Stores`.

**Next action:** User extracts ZIP outside production folder; run 1_INSTALL_SOURCE.cmd, 2_BUILD_SAFELY.cmd and only after staging succeeds 3_ACTIVATE_MAIN_APP.cmd during approved maintenance window; provide run output for QA. If service-manager checks fail, use existing supervisor restart procedure instead of forcibly killing processes. Verify same QR counts, Today/Weekly/Test Monitor/Sheets and a printed QR scan after cutover.

**GitHub current status:** this Markdown handoff was updated; the new frontend source was delivered in ZIP and is **NOT** committed to GitHub main. Earlier branches remain unmerged; do not claim one-branch consolidation is complete. No production services or DB were changed by ChatGPT.

## 2026-10-09 QR count-gate bug fix (Windows report build)

User attempted 2_BUILD_SAFELY.cmd for the compact Geo & Store Analytics main-web update and received:
`STOP: Live API reports only 1 QR codes: stopping to protect data`.
The script had used `$codes = @(Get-Json 'http://127.0.0.1:3550/api/v1/qr-codes')` and `$codes.Count` which can count the PowerShell JSON array wrapper rather than the contained QR records. The backend endpoint returns QR records; the main app screenshot and root database had previously shown 50 QR records and 1615 raw scan rows. This failure happened BEFORE staging build and before any process restart.

**Patch:** `NextToppers_QR_Compact_Main_Web_FIXED_QR_Count_2026-10-09.zip`
**SHA256:** `24f2ab27b30ff0a8ff05605f201aeb15e7dd60c08cd05e6eb4abc9f565d3affc`
**Status:** Delivered as ZIP in chat. NOT COMMITTED AS FULL PRODUCTION SOURCE. User must extract fresh ZIP and run **2_BUILD_SAFELY.cmd only** if Step 1 source was already installed. Do not reinstall previous source patch.

Repaired `PREPARE_AND_ACTIVATE.ps1`:
- Uses `GET /api/v1/qr-scale/codes?limit=10&active=all` and its scalar `.total` rather than `@(Get-Json /api/v1/qr-codes).Count`.
- Keeps root DB identity check and historical scan count guard; does not hardcode 50, so creates new QR codes without modifying script.
- Replaces the flawed post-restart and final QR counts, avoiding identical false stops after building.
- Improved `2_BUILD_SAFELY.cmd` outcome handling; failure does not pretend build passed.
- Existing QR redirect / edge Worker / KV / application database untouched.
- Test results: 4 static/dynamic safety-gate source tests PASS, 4 synthetic installer tests PASS, 3 Python/FastAPI synthetic report tests PASS (with isolated PYTHONPATH setup), ZIP integrity PASS.
- Neither this PowerShell script nor the web build was executed on the physical Windows server, and no live restart is claimed.
- Stage first, confirm `STAGED BUILD PASSED`, then review process supervisor and run controlled restart only with appropriate acceptance.

Potential remaining caveats: The auto cutover still requires a stable matched launcher for Python+Node and an approved maintenance window; STOP means do not bypass guards. Full Windows go-live not yet accepted.


## 2026-10-09 — Second staging blocker fixed: PowerShell parser syntax error

User ran prior `2_BUILD_SAFELY.cmd` (fixed QR count package) and got:
`PREPARE_AND_ACTIVATE.ps1:202 char:1 Unexpected token '}' in expression or statement.`

**Root cause verified from exact supplied package:** two accidentally doubled closing quotation marks in `PREPARE_AND_ACTIVATE.ps1`:
- line 172: `Info "Updated API PASS. QRs=$updatedCount, verified QR scans=$($report.verified_scans)""`
- line 201: `Info "Database unchanged; verified scan count $($bridge.verified_scans), QR codes $finalQrCount""`
The malformed strings invalidated PowerShell parsing before any build/restart.

**New self-contained replacement ZIP delivered in chat:**
`NextToppers_QR_Compact_Main_Web_POWERSHELL_PARSER_FIXED_2026-10-09.zip`
SHA-256: `8f3e26bb175b266de29dc5455aee7d6e376d07fe4e51e2d84d303e109d142ef2`
18 package entries, ZIP integrity PASS. Test result 7/7 targeted offline static/guard unit tests PASS. Full Windows PowerShell parser and Next staging build still require execution on the user Windows host (no PowerShell executable on build machine; do not misrepresent offline tests as Windows parser verification).

**Changes:**
- Removed both extra quotes in staged build + go-live PowerShell script without relaxing any database identity or backup gate.
- New `CHECK_POWERSHELL_SYNTAX.ps1` calls Windows built-in `[System.Management.Automation.Language.Parser]::ParseFile`, reports exact parser lines and exits nonzero on any error.
- `2_BUILD_SAFELY.cmd` and `3_ACTIVATE_MAIN_APP.cmd` call the syntax gate before invoking the deployment script.
- Added explicit test coverage for both broken lines and parser gate; excludes previous test cache from new ZIP.

**User action:** extract replacement ZIP to a new folder, do not repeat Step 1/source installation, run `2_BUILD_SAFELY.cmd` only. On `STAGED BUILD PASSED`, review real running process configuration before considering Step 3. No services restarted by ChatGPT; previous reported parsing error itself ran before any build/restart. Do not switch to divergent 23-QR DB. Root expected live DB with 50+ QR codes remains `D:\timetable-intelligence-platform\data\timetable.db`.

The replacement ZIP is a conversation artifact, not a GitHub source commit. Branch consolidation and production cutover remain pending.


## 2026-10-09: Step 2 Next.js 16 Turbopack junction failure (Webpack staging remedy)

**Exact user-supplied physical Windows result:**
- Windows PowerShell parser PASS.
- Live API: 50 QR codes; selected root DB: 50 QR codes, 1,722 raw scans.
- SQLite consistent snapshot integrity PASS; backup recorded at D:\\timetable-intelligence-platform\\backups\\qr_compact_go_live_20261009-161039\\consistent-before-cutover.db.
- Next.js TypeScript `tsc --noEmit`: PASS.
- Next 16.2.12 default Turbopack production build: FAILED before cutover with
  `Symlink [project]/node_modules is invalid, it points out of the filesystem root`.
- Existing website was not deliberately restarted. Existing live `.next` unchanged.

**Root cause:** The stage script copied the web source into `backups/.../web-staged` and linked its `node_modules` to `apps/web/node_modules` via a Windows junction. Turbopack's project filesystem-root restriction rejects that outside-root link. This is documented in Next.js (the `--webpack` flag is the official Next 16 Webpack build opt-out; GitHub next.js issue #88335 discusses this exact symlink fault). It is not evidence of lost QR data.

**Delivered candidate ZIP:**
`NextToppers_QR_Compact_Main_Web_WEBPACK_BUILD_FIXED_2026-10-09.zip`
SHA-256 `deb bbe80` WITHOUT space => `debbbe80bd8bb07ce05faca3e70e6066eb4200636f5abc3bba32d5f32ee23d05`.

Change is deliberately ONE line in existing `PREPARE_AND_ACTIVATE.ps1`:
`& npm.cmd run build` --> `& npm.cmd run build -- --webpack`.
All other original package files are untouched; added only help documentation and a dedicated test file. Build command executes `npm run build -- --webpack`, which becomes `next build --webpack` for existing `package.json`.

**Validation completed in isolated tooling:**
- Exact original script bytes compared after reversing single-line substitution: same, one change only.
- ZIP CRC/integrity PASS.
- 15 separate targeted Python tests PASS (four Webpack build guard tests, three parser guard tests, four QR count tests, four compact installer tests).
- Full Windows staging Webpack build NOT run by ChatGPT; needs user Windows. The official Webpack option is documented, but this environment cannot confirm compilation of the real app.
- No live API/web stop/restart, no DB mutation, no Cloudflare changes, no QR image/redirect changes.

**Next user action:** extract the new ZIP to a fresh Downloads folder; SKIP `1_INSTALL_SOURCE.cmd` because source is already installed; execute only `2_BUILD_SAFELY.cmd`, which runs syntax gate, QR count vs root database identity check, consistent backup, strict TypeScript and staging `next build --webpack`. Do NOT run Step 3 until `STAGED BUILD PASSED` and process supervision/cutover have been reviewed. If the Webpack build itself fails, preserve the exact error message and don't repeatedly install source or change databases.

**Remaining high-risk task:** Carefully review actual API/web supervisor and restart mechanism before executing `-GoLive`. Older script force-stops processes; do not assume automatic cutover is safe even after the staging build passes.


## 2026-10-09 — Real Windows staging build PASS (reported by user)

User reran STEP 2 from WEBPACK_BUILD_FIXED ZIP.
- Windows PowerShell syntax verification PASS.
- API QR count matched selected root data DB: 50 vs 50; raw scan count previously measured as 1,722.
- Consistent SQLite snapshot backup PASS.
- `npm run typecheck` with `tsc --noEmit` PASS.
- Next.js 16.2.12 `next build --webpack` compiled successfully (4.7 s), completed TypeScript, produced all 18/18 pages.
- Next build route list includes `/qr/reports`.
- STAGED BUILD PASSED at `D:\timetable-intelligence-platform\backups\qr_compact_go_live_20261009-161907\web-staged\.next`.
- No intentional API/web restart, no live `.next` swap. All historical QR data retained.

**Next acceptance gate**: physical Windows production activation to 3550+3500 remains PENDING. WARNING: the package `3_ACTIVATE_MAIN_APP.cmd` executes `PREPARE_AND_ACTIVATE.ps1 -GoLive`, which **runs a new staging backup and build again, then forcibly stops the identified API and web processes and replaces them with newly launched processes**. The API stop/start portion does not automatically restore the previous API process if startup or new report endpoint health check fails. Therefore do NOT describe this as risk-free or as an already tested go-live. Review which supervisor/task launches both live processes and establish explicit manual recovery path before running it during a maintenance window. Backend `app.config` loads project root .env files and falls back to cwd-relative DB path; ensure the new process pins the verified root 50-QR DB and retains required notification/service configuration. Validate API health, QR count, scan counts, old printed QR, main dashboard, timetable, sources/test monitor, /qr/reports and PDF/CSV after cutover.

The full original working-source ZIP and candidate patch were delivered in chat; GitHub main still contains only standalone reporting tools and continuation documents, not a complete accepted Windows web/API release.
