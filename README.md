# NextToppers Timetable + QR

The app itself runs on the Windows server in `D:\timetable-intelligence-platform`
(API on port 3550, website on port 3500, QR links through the Cloudflare Worker `q`).
This GitHub repository holds **safe helper tools and notes**. Pulling it never changes
the running app.

## Folders

| Folder | What it is |
|---|---|
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

## QR reports

See [docs/QR_REPORTS_GUIDE.md](docs/QR_REPORTS_GUIDE.md).

## Never put in GitHub

Databases, scan records, `.env` files, Cloudflare tokens, passwords, OAuth files,
Google Sheets data, customer data or logs with private details.
