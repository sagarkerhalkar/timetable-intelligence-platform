# 2026-08-17 - QR DB split identified after reboot

## User report
The working app returned after Windows restart. Timetable, Test Monitor, Sheet-related screens and other non-QR functions are working and must remain untouched. QR appears to show the old set/UI.

## Read-only evidence
Current runtime:
- Web 3500: Next.js production start from `D:\timetable-intelligence-platform\apps\web`
- API 3550: uvicorn from `D:\timetable-intelligence-platform\services\api`
- Protected 3457: not listening

Two healthy SQLite DBs exist:

### Service DB - newer QR set
`D:\timetable-intelligence-platform\services\api\data\timetable.db`
- integrity: ok
- qr_codes: 23
- qr_scans: 4
- qr_templates: 3
- newest QR rows created 2026-08-14
- sample latest slug: `vg3785v` (Economics 12th)

### Root DB - older QR set
`D:\timetable-intelligence-platform\data\timetable.db`
- integrity: ok
- qr_codes: 24
- qr_scans: 24
- qr_templates: 1
- newest QR rows created 2026-08-12
- sample latest slug: `mw9jmyn` (Applied Maths 11th)

## QR frontend/API/Worker state
- `apps\web\app\qr\stats\page.tsx` hash matches the v1.0.26.1 regression-fixed stats page.
- Main QR page is newer/modified and contains NextToppers/Bulk/Templates tokens.
- QR fast API source is the lightweight version and does not contain later edge-sync/cron code.
- Public Worker is healthy with `x-ntqr-fast=3`, `x-ntqr-source=edge-kv`, `edge_kv=true`.

## Important inference to verify
The user's visible old QR set can be explained if the rebooted API is serving the root DB instead of the service DB. Because historic configuration used a relative SQLite URL, actual DB selection can depend on process working directory. Process command line alone does not reveal the active SQLite file.

## Next safe action
Do NOT deploy, restart, merge, delete or migrate anything yet.
Perform one read-only API identity check:
- GET local `http://127.0.0.1:3550/api/v1/qr-codes`
- If latest slug is `vg3785v`, runtime is serving the newer service DB.
- If latest slug is `mw9jmyn`, runtime is serving the older root DB.

Only after that result should QR-only recovery be applied. Non-QR modules remain frozen.

## Locked performance target
QR redirect target remains <=0.6s for the redirect response, using Cloudflare edge lookup + immediate redirect; no synchronous local API/Tunnel call before redirect.
