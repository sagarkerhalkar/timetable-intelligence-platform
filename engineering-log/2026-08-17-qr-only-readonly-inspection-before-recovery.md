# 2026-08-17 - QR-only read-only inspection before recovery

## User requirement
Keep the currently restarted/working timetable application frozen because Sheets, Time Table, Test Monitor, Sheet Updates and other pages are working correctly. Investigate and recover only the QR area. QR redirect target remains <=0.6 second for the redirect response.

## Current known live state from user output
- Web port 3500 is listening with Next.js start from `D:\timetable-intelligence-platform\apps\web`.
- API port 3550 is listening with uvicorn from `D:\timetable-intelligence-platform\services\api`.
- Protected dev port 3457 is not listening in the captured state and must remain untouched.
- Local web `/` returned HTTP 200 in 46 ms.
- Local API `/api/v1/qr-fast/health` returned HTTP 200 in 8 ms.
- Public Worker `https://q.nexttoppers.workers.dev` returned HTTP 200 with `x-ntqr-fast=3`, `x-ntqr-source=edge-kv`, `edge_kv=true`.
- Previous generic read-only checker had a PowerShell helper-name bug: function `H` conflicted with PowerShell alias `h`/`Get-History`, causing section-header errors. Those errors were checker errors, not app errors.

## Next action
Do not deploy another QR update yet. Run a new QR-only read-only checker that only determines:
1. Whether new QR records still exist in the authoritative service DB and/or historical root DB.
2. Which QR frontend source/build is present after reboot.
3. Which QR API source is present.
4. Current public Worker health/marker.

The checker performs no restart, DB write, Worker deploy/rollback, KV write/delete, or source modification.

## Artifact
`NEXTTOPPERS_QR_ONLY_READONLY_CHECK.zip`

SHA-256: `ffe9dbb6037d4407b0a25cba5e589e4281c799daca4bfe61f512c09c6be45020`

ZIP CRC: PASS.

## Acceptance decision after report
- If new QR rows are present in the authoritative service DB: restore/persist only the QR frontend and fast QR path; do not touch timetable modules or DB.
- If rows exist only in the historical root DB: back up both DBs first and prepare an explicit QR-only merge, never replace the authoritative DB.
- If rows are absent from both DBs: inspect remaining Worker/KV and source evidence before any recovery write.
