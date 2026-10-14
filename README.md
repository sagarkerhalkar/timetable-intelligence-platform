# NextToppers Timetable + QR

The app itself runs on the Windows server in `D:\timetable-intelligence-platform`
(API on port 3550, website on port 3500, QR links through the Cloudflare Worker `q`).
This repository holds the app's source code (copied from the server on 14 Oct 2026,
without databases, `.env` files, passwords, logs or build output) and safe helper tools.
Pulling it never changes the running app; only the update scripts below do, and
each one backs up first and checks the app afterwards.

## Folders

| Folder | What it is |
|---|---|
| `services/api/` | QR + timetable API (Python, port 3550) |
| `apps/web/` | Website (Next.js, port 3500) |
| `worker/` | Cloudflare Worker `q` that answers every QR scan (not deployed from here) |
| `tools/qr-fast-sync/` | Update: QR create/edit talks to Cloudflare directly; fast and clear errors |
| `tools/cloudflare-token-fix/` | Fixes "Cloudflare QR sync failed; QR creation was rolled back" |
| `tools/qr-insights/` | Read-only QR reports (country, city, device) as CSV and PDF, and a safe database backup |
| `tools/local-source-audit/` | Makes a source-only review ZIP of the server app (no secrets, no database) |
| `docs/` | Guides and history |

Old code is not on `main`. Every old branch is kept in one branch,
`archive/old-branches-2026-10-14`; its README lists them and how to bring one back.

## Fix: "Cloudflare QR sync failed; QR creation was rolled back"

**Why:** since 9 Oct 2026 the QR API starts in the background as the Windows SYSTEM
account (task `NextToppers-AutoRecovery`). SYSTEM cannot use your Cloudflare login,
so it needs a Cloudflare API token. The token set on the server is not valid
(`Invalid access token [code: 9109]`), so every new QR is rolled back.
Your existing QR codes keep working; only creating or editing QRs is blocked.

**Fix** (PowerShell, **Run as administrator**, on the server):

```powershell
$Review = Join-Path $HOME "NextToppers-Review"
if (Test-Path (Join-Path $Review ".git")) { git -C $Review pull --ff-only origin main } else { git clone https://github.com/sagarkerhalkar/timetable-intelligence-platform.git $Review }
powershell -ExecutionPolicy Bypass -File "$Review\tools\cloudflare-token-fix\FIX_QR_CLOUDFLARE_TOKEN.ps1"
```

The script shows how to create the token, tests it with Cloudflare (read-only),
saves it for the computer and restarts only the QR API. It never changes QR codes,
scans, the database, Cloudflare KV or the Worker. Add `-CheckOnly` to only look.

## Update: fast QR sync (14 Oct 2026)

Creating or editing a tracked QR used to start Cloudflare's Wrangler tool several
times through `npx`, which took up to minutes and showed long coloured error text.
The API now calls Cloudflare's API directly: a few seconds, short clear errors.
Only `services/api/app/services/qr_edge_runtime.py` changes in the live app
(plus two test files). Database, QR codes, scans, website and Worker are untouched.

Run on the server (PowerShell, **Run as administrator**), after the token fix above:

```powershell
$Review = Join-Path $HOME "NextToppers-Review"
git -C $Review pull --ff-only origin main
powershell -ExecutionPolicy Bypass -File "$Review\tools\qr-fast-sync\UPDATE_QR_FAST_SYNC.ps1"
```

It stops if the live file is not the reviewed version, tests the new code in a
temporary copy, backs up, restarts only the QR API, and checks the number of QR
codes and scans. If a check fails it puts the old file back by itself.

## QR reports

See [docs/QR_REPORTS_GUIDE.md](docs/QR_REPORTS_GUIDE.md).

## Never put in GitHub

Databases, scan records, `.env` files, Cloudflare tokens, passwords, OAuth files,
Google Sheets data, customer data or logs with private details.
