# NextToppers — Timetable + QR (beginner guide)

> **Important: this public GitHub repository is NOT yet a verified complete copy of the app that is running on the Windows server.**
> Do not replace the running application, reset a database, deploy Cloudflare Worker, or install old ZIP packages directly from GitHub. This page provides a **safe, working, standalone QR reporting workflow** for Windows and Linux and describes what is still missing from a full-app installer.

## Start here: what does each thing mean?

| Name | Easy meaning |
| --- | --- |
| **main** | Our official GitHub front door for future approved code and instructions |
| **Live app** | The NextToppers website and QR system people are already using |
| **Database** | The file holding QR codes, QR scan history, timetable and related records |
| **Backup** | An extra copy kept in a different folder so the original stays safe |
| **QR reports** | Read-only CSV/PDF results from a backed-up database |
| **Draft** | Code still being checked; not safe to install into the live app |

**One rule:** GitHub code and your live server are not automatically the same. Pulling GitHub changes does NOT safely upgrade the running website.

## What works from main today?

- **Offline read-only QR reports:** country; state/region and city if stored; district only if already known (often Unknown); OS/browser/device category and repeated anonymized browser IDs for each QR.
- **Download reports:** locations.csv, device_types.csv, devices_per_qr.csv, store_qr_traffic.csv and qr_insights.pdf.
- **QR-to-store traffic:** see tracked QR scans to Google Play / Apple App Store. These are not confirmed downloads or installs.
- **Consistent SQLite backup helper:** reads the source database in SQLite read-only mode and writes a separate snapshot plus counts and SHA-256 manifest.

**Not completed:** live Analytics menu integration, app-store install attribution integrations, full working server source recovery, unattended Windows full-app installer, native Linux full-app installer, and production acceptance testing.

## Windows: easiest safe report installation (PowerShell)

Use these steps on the Windows server or on a separate Windows computer with a verified database copy. Keep the website and API running. **Do not run git pull, reset, checkout, npm, pip package upgrades or an older installer inside the live D:\timetable-intelligence-platform folder.**

### Step 1 — Check prerequisites

1. Press Start, type **PowerShell**, and open it.
2. Copy and paste each command, then press Enter.
3. Check you have Git and Python. Install official Git and Python if a command says Not Found.

~~~powershell
git --version
py --version
~~~

### Step 2 — Download a SEPARATE review copy (not your production folder)

~~~powershell
cd $HOME
git clone https://github.com/sagarkerhalkar/timetable-intelligence-platform.git NextToppers-Review
cd NextToppers-Review
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install "reportlab>=4"
~~~

If you already made this review folder, use the following two commands IN THAT REVIEW FOLDER instead of cloning again:

~~~powershell
cd "$HOME\NextToppers-Review"
git pull --ff-only origin main
~~~

If Git reports local changes or a merge conflict, stop. Do not use reset --hard.

### Step 3 — Find and confirm the ACTUAL active database

The historical *expected* Windows path is:

D:\timetable-intelligence-platform\services\api\data\timetable.db

But a previous incident showed a second, divergent database at D:\timetable-intelligence-platform\data\timetable.db. The existence of a file does not prove your running API uses it. **Confirm the active DATABASE_URL / API service configuration first.** Never replace one database with the other.

Check that the expected file is present (read-only check):

~~~powershell
Test-Path "D:\timetable-intelligence-platform\services\api\data\timetable.db"
Get-NetTCPConnection -LocalPort 3550 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess
~~~

If the file is missing, the API is not listening on your expected port, or the active path is uncertain: STOP. These instructions must not guess your production database.

### Step 4 — Make a safe, consistent backup (NO service restart)

Only after you have verified the active database path:

~~~powershell
$DB = "D:\timetable-intelligence-platform\services\api\data\timetable.db"
$BackupFolder = "D:\NextToppers-Offline-Backups"
.\.venv\Scripts\python.exe tools\qr-insights\safe_snapshot.py --source "$DB" --backup-dir "$BackupFolder"
~~~

A new timetable-backup-...db and matching .manifest.json appear in the separate backup folder. The script uses SQLite's backup API (not a normal file copy, which can miss WAL changes). Check that the manifest says integrity_check: ok and includes the QR/timetable counts. Keep this folder **private** and do not upload it to this public GitHub repository.

### Step 5 — Make your CSV and PDF reports FROM THE BACKUP

~~~powershell
$Copy = (Get-ChildItem "D:\NextToppers-Offline-Backups\timetable-backup-*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1).FullName

.\.venv\Scripts\python.exe tools\qr-insights\qr_insights.py --database "$Copy" --output-dir "$HOME\NextToppers-QR-Reports"

Invoke-Item "$HOME\NextToppers-QR-Reports"
~~~

Open qr_insights.pdf, locations.csv, device_types.csv or devices_per_qr.csv. This does not change your live app screen. It also does not write to the original database or the Cloudflare Worker.

For one QR only, append: --qr-id ACTUAL_INTERNAL_QR_ID

## Linux: safe report-only installation (Ubuntu example)

**The whole NextToppers timetable/QR web application is NOT certified to install on Linux from this GitHub repository yet.** These steps install only the offline QR reporter using a verified SQLite file COPY transferred securely to your Linux computer.

1. Open **Terminal**.
2. Paste these commands:

~~~bash
git --version
python3 --version
cd "$HOME"
git clone https://github.com/sagarkerhalkar/timetable-intelligence-platform.git NextToppers-Review
cd NextToppers-Review
python3 -m venv .venv
./.venv/bin/python -m pip install "reportlab>=4"
~~~

If virtual environment creation fails on Ubuntu because venv is unavailable, install your distribution's python3-venv package first. Do not use sudo pip to install dependencies globally.

3. Put a verified offline timetable.db copy in $HOME/NextToppers-Input/timetable.db (do not copy secrets; protect the file).
4. Make a separate, consistent local snapshot and create reports:

~~~bash
./.venv/bin/python tools/qr-insights/safe_snapshot.py \
  --source "$HOME/NextToppers-Input/timetable.db" \
  --backup-dir "$HOME/NextToppers-Offline-Backups"

COPY="$(ls -t "$HOME"/NextToppers-Offline-Backups/timetable-backup-*.db | head -n 1)"
./.venv/bin/python tools/qr-insights/qr_insights.py \
  --database "$COPY" --output-dir "$HOME/NextToppers-QR-Reports"
~~~

Open the NextToppers-QR-Reports folder and read the CSV/PDF files. If you have no trusted SQLite copy yet, STOP instead of experimenting on the live database.

## How to update later

**For the safe REPORT tools only:** Go to your $HOME/NextToppers-Review folder and run git pull --ff-only origin main; then use Steps 4–5 again. This changes only the isolated review copy. It is not a production website update.

**For the complete LIVE app:** There is no approved one-command installation or update yet. First reconcile the exact running Windows source, backup paths and GitHub history; build a complete reproducible release; test it against an isolated staging database; verify timetable, tests, QR destinations, Cloudflare KV and scan counts; then provide a tested installer with rollback. Never install a historical ZIP merely because it appears newest.

## Stores: very important distinction

- **Scan count:** how many verified QR browser events reached the QR redirect flow.
- **Store-link QR traffic:** scans on QR records whose destination is Google Play / Apple App Store.
- **Confirmed app downloads / installs:** data independently supplied by Google Play Console or App Store Connect. Existing anonymous scans cannot reliably prove how many people installed an app. QR-specific campaigns need store-supported attribution setup.

The report deliberately displays **Not connected** for actual downloads until verified store data is available. District is reported as **Unknown** when the geo provider only supplies state/region or city. Anonymous browser/device IDs are not device serial numbers or people.

## GitHub branches: why they are NOT deleted yet

This repository currently has historical and divergent release branches. Many historical branches are ancestors of nexttoppersqr; several agent branches and the worker gateway branch have divergent commits. The complete running production source has not been verified against any one branch.

**Official future target: main only, with an archived version history.** Until reconciliation, keep the old Git references as recovery evidence. Blind merges or branch deletion would risk losing unfinished fixes. See docs/BRANCH_CONSOLIDATION_2026-10-09.md. No production deployment is triggered by this README.

## Do not put these things in public GitHub

Do not push: databases, scan records, private Google Sheets, passwords, .env files, Cloudflare tokens, OAuth files, App Store / Play Console credentials, email addresses, customer data, uploads or runtime logs containing private details.

## Source and next steps

- QR reporter: tools/qr-insights/qr_insights.py (offline candidate copied from the read-only analytics branch).
- SQLite backup tool: tools/qr-insights/safe_snapshot.py (tested against an isolated sample database).
- Operating context: nexttoppersqr/docs/CURRENT_PROJECT_CONTEXT.md on the historical QR branch.
- Full release acceptance status: **PENDING**, particularly Windows live-source verification and Linux full-app support.

If anything fails, take a screenshot of the exact error and keep your live website running. Do not fix a reporting error by changing the live DB location, restarting Cloudflare, or deleting old QR entries.


## Have a live Windows installation without Git? Prepare a private source REVIEW ZIP

**This is the next action for the real Windows server that reported "fatal: not a git repository."**
The API is running on port 3550 and the web UI is running on port 3500. Do not run git init or git pull inside D:\timetable-intelligence-platform.

Open PowerShell and paste the entire block:

~~~powershell
$Review = Join-Path $HOME "NextToppers-Review"
if (-not (Test-Path (Join-Path $Review ".git"))) {
    git clone https://github.com/sagarkerhalkar/timetable-intelligence-platform.git "$Review"
} else {
    git -C "$Review" pull --ff-only origin main
}
if ($LASTEXITCODE -ne 0) { throw "Review source download failed; stopped safely." }

$Desktop = [Environment]::GetFolderPath("Desktop")
$Zip = Join-Path $Desktop ("NextToppers-Working-Source-Review-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".zip")
$Python = "C:\Users\Pc\AppData\Local\Python\pythoncore-3.14-64\python.exe"
& $Python (Join-Path $Review "tools\local-source-audit\prepare_source_review.py") --root "D:\timetable-intelligence-platform" --output "$Zip"
~~~

This creates a **source-only review ZIP on the Desktop**, separate from the working app. It is NOT a deployable installer and is NOT a production database backup. It intentionally skips .env, databases, private keys, tokens, logs, build outputs, node_modules, uploaded assets and similar folders; some necessary private configuration will therefore not be included. It also skips files that look like they contain embedded secrets.

**Mandatory human review:** Automated screening cannot guarantee that source code contains no hardcoded secrets. Inspect the archive before sharing it privately for reconciliation. NEVER upload the ZIP directly to this public repository.

Once the sanitized source has been reviewed, we can reconcile the live files against old branches, add reproducible complete source and test releases into main, and only THEN retire unneeded branches. Until that happens, git pull is *not* a safe method to update the running app.
