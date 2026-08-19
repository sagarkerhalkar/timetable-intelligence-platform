# 2026-08-17 - Read-only checker alias bug and live QR state

## User report
The user ran `RUN_READONLY_CHECK_NOW.cmd` and reported repeated PowerShell errors such as:

`Get-History : Cannot bind parameter 'Id'. Cannot convert value "PORTS" to type "System.Int64".`

The same occurred for headings such as `LOCAL HTTP`, `PUBLIC WORKER`, and `CLOUDFLARE WRANGLER READ ONLY`.

## Root cause
The read-only checker defined a helper function named `H`, but in PowerShell `h` is an alias for the built-in `Get-History` cmdlet. The calls such as `H "PORTS"` therefore resolved to `Get-History` instead of the intended helper function. This is a bug in the checker script, not an application failure.

## Useful live-state evidence that still executed
- Port 3457: not listening.
- Port 3500: listening via Node/Next.js from `D:\timetable-intelligence-platform\apps\web`, command `next start -p 3500 -H 0.0.0.0`.
- Port 3550: listening via the service virtualenv Python, command `uvicorn app.main:app --host 0.0.0.0 --port 3550`.
- `http://127.0.0.1:3500/`: HTTP 200 in 46 ms.
- `http://127.0.0.1:3550/api/v1/qr-fast/health`: HTTP 200 in 8 ms.
- Public Worker `https://q.nexttoppers.workers.dev/__ntqr_health`: HTTP 200 in 373 ms, `x-ntqr-fast=3`, `x-ntqr-source=edge-kv`, body reports `service=NextToppers QR Edge KV`, `fast_path=true`, `edge_kv=true`.
- Public Worker root: HTTP 200 in 70 ms with the same `x-ntqr-fast=3` and `x-ntqr-source=edge-kv` markers.

## Interpretation
The new QR backend/edge work has not disappeared entirely after reboot: the local `qr-fast` API is live and the public Worker is still an edge-KV build marked `x-ntqr-fast=3`. The old QR appearance in the web app therefore most likely reflects the persisted Next.js web build/UI that Windows started on port 3500, while newer QR backend/Worker pieces remain live. Do not infer that newly created QR database rows are deleted until the production DB is inspected.

## User direction
The user explicitly states that Sheets, timetable, tests, and other app options are working correctly after reboot and must not be touched. Freeze those components. Future work is QR-only.

## Next engineering action
Do not deploy another QR update yet. Use the current evidence to isolate the QR UI/build persistence issue and inspect QR DB records only. If another checker is needed, avoid aliases/single-letter PowerShell function names; use a unique name such as `Write-Section`.
