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

## Update: QR speed and scan safety (19 Nov 2026)

**Why:** QR pages (My QR Codes, QR Analytics, Geo & Device Analytics) took 2–4 s and
sometimes failed. Every QR page request re-ran the whole QR database setup script
(including DROP/CREATE TRIGGER), which needs the database write lock. Requests queued
behind each other and behind scan inserts. A scan that waited more than 5 s failed,
and because the Worker sends each scan only once, that scan was lost.

**What changes** (QR API only): the setup script runs once; "recent scans" reads the
newest rows directly instead of sorting all scans; analytics (10 s) and geo/device
reports (60 s) share a short cache; a scan that hits a busy database is retried
(a repeated scan is never counted twice). Nothing in the database changes.

Measured on a copy with 400,000 scans: recent scans 160–225 ms → under 1 ms; reports
reloads ~380 ms → under 1 ms; with 6 dashboards open while scans arrive, dashboard
calls went from 540 ms typical (10 lock errors) to 1 ms (no errors).

Run on the server (PowerShell, **Run as administrator**), preferably at a quiet time:

```powershell
$Review = Join-Path $HOME "NextToppers-Review"
git -C $Review fetch origin
git -C $Review checkout fix/qr-speed-and-scan-safety   # or main, after the PR is merged
powershell -ExecutionPolicy Bypass -File "$Review\tools\qr-speed-fix\UPDATE_QR_SPEED_FIX.ps1" -CheckOnly
powershell -ExecutionPolicy Bypass -File "$Review\tools\qr-speed-fix\UPDATE_QR_SPEED_FIX.ps1"
```

Same safety as the fast-sync update: it stops if the live files are not the reviewed
version, tests in a temporary copy, backs up, restarts only the QR API, compares QR
and scan counts, and puts the old files back by itself if any check fails.

**Step 2 (19 Nov evening):** `routes.py` now draws each QR image once and reuses it
(memory + `data\qr_image_cache`). Drawing one image took 0.2–0.4 s of CPU, and
My QR Codes drew 25 on every open (~6 s measured live), which slowed the whole API.
Same QR + same design always gives the same image bytes; an edited design, link or
logo gets a new image. Run the same two commands again after `git -C $Review pull`.

Two more changes in this branch take effect only when deployed separately:

- `worker/src/index.js` – the Worker retries a scan confirmation (after 1.5 s and 5 s)
  when your server is busy or restarting. Deploy it the way the Worker `q` is normally
  deployed.
- `apps/web/components/navigation-links.tsx`, `qr-product-nav.tsx` – menu links no
  longer fully pre-render every page in the background (each page open used to
  render ~14 other pages on the server). Takes effect at the next website build.

## Update: QR Insights, new analytics and one-link sharing (19 Nov 2026)

**What you get**
- New **QR Analytics** page (`/qr/stats`): verified scans with change vs the previous period,
  unique and returning devices, daily trend, busiest hours and weekdays, sources, states,
  cities, mobile networks, devices, top QR codes and a live feed. Works in light and dark mode
  on phone, tablet and desktop.
- **One link for everything.** There are no separate WhatsApp/Instagram/Facebook links.
  Sources are recognised automatically: Google Lens / Google app, Google Search, YouTube,
  Gmail and WhatsApp (Android) from what the phone reports; Instagram, Facebook, Snapchat,
  LinkedIn and X from their in-app browsers (new scans). Camera scans that report nothing are
  shown honestly as "Not reported".
- Old scans are re-read with the better labels: nothing in the database is changed.
- Location: state is reliable; the city is the network's city (often the operator's hub city on
  Indian mobile data) and is labelled as approximate. Mobile network (Jio, Airtel, Vi, BSNL…) shown.
- My QR Codes: one-link Share window (copy, WhatsApp, Telegram, Facebook, X, Email, SMS, phone
  share sheet, PNG/SVG/PDF); phones now open the list as cards (it was empty on phones).
- Refreshed QR tab bar (sticky, dark mode).

**Install** (PowerShell, **Run as administrator**, at a quiet time; the website is offline
for about 10–60 seconds while it restarts, QR codes keep working):

```powershell
$Review = Join-Path $HOME "NextToppers-Review"
git -C $Review pull
powershell -ExecutionPolicy Bypass -File "$Review\tools\qr-insights-update\UPDATE_QR_INSIGHTS.ps1" -CheckOnly
powershell -ExecutionPolicy Bypass -File "$Review\tools\qr-insights-update\UPDATE_QR_INSIGHTS.ps1"
```

It also installs the earlier speed fix and QR image cache if they are not installed yet.
The website is built in a separate copy first; the live site is changed only if that build
succeeds, and it is put back automatically if any page check fails.

## QR reports

See [docs/QR_REPORTS_GUIDE.md](docs/QR_REPORTS_GUIDE.md).

## Never put in GitHub

Databases, scan records, `.env` files, Cloudflare tokens, passwords, OAuth files,
Google Sheets data, customer data or logs with private details.
