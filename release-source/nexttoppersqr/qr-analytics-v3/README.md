# NextToppers QR Geo, Device & Official Store Reports — v3 (2026-10-09)

**Scope:** Additive review candidate based on the existing nexttoppersqr branch. It does not change QR images/slugs/target links, Cloudflare Worker/KV, original Statistics, or live timetable data.

## Implemented endpoints and UI

- GET /api/v1/qr-reports/summary?qr_id= : verified scans, country / state / city / district (when known), pseudonymous device repeat counts, per-QR totals.
- GET /api/v1/qr-reports/scans.csv?qr_id= : streamed, formula-protected per-scan CSV for all verified scan rows.
- GET /api/v1/qr-reports/summary.pdf?qr_id= : formatted geography/device/per-QR summary (requires reportlab).
- GET /api/v1/qr-reports/stores : imported official aggregate store metrics, **not** purported QR installs.
- New /qr/reports web page with QR selector, geography and device tables, PDF/CSV links and honest store totals.
- Local offline importer for Google Play installs-country CSV and Apple App Store Downloads TSV/CSV/txt.gz reports; duplicate identical files ignored, overlapping dates replaced not added.

## Accuracy and privacy contract

1. QR scans are **not installs**. Play reports include Daily User Installs; Apple reporting separates first-time downloads, redownloads and more. Preserve these labels.
2. To attribute future installs to an **individual QR**, add a unique QR campaign to the Google Play destination and integrate Play Install Referrer *inside the Android app*. For Apple, configure App Store campaign links and import detailed App Store Downloads with Campaign tokens. Existing untagged QR scans cannot retroactively prove installs.
3. Cloudflare provides approximate country/state-region/city. It does not reliably provide district. Show Unknown rather than treating city as district.
4. Browser visitor hash is a pseudonymous browser-scoped identifier, not guaranteed to represent one physical device. Exact model is often unavailable.
5. Only confirmed=1 scans are counted here. Legacy and unverified scans are excluded.
6. API summaries contain top 1,000 grouped results; CSV streams raw rows. Millions of scans need materialized aggregation/production architecture before claiming scale readiness.
7. Store data is unconnected until publisher report files are locally imported; there are no fabricated figures.
8. Apple API download reports may consist of multiple segments per date. **Consolidate all segments for a date into one complete report before importing**. Do not mix detailed and standard exports for the same reporting period.
9. Offline store imports write only to a separate qr_store_reports_v3.sqlite3 file. Never to timetable.db.
10. These reporting URLs follow the existing analytics access boundary. Apply proper admin authorization before exposing analytics publicly.

## Safe Windows preflight and installation

From the Windows application checkout:

~~~powershell
cd D:\timetable-intelligence-platform
git fetch origin feature/qr-geo-device-store-reporting-20261009
git checkout origin/feature/qr-geo-device-store-reporting-20261009 -- release-source/nexttoppersqr/qr-analytics-v3
py release-source/nexttoppersqr/qr-analytics-v3/INSTALL_QR_REPORTS_V3.py --app-root D:\timetable-intelligence-platform
~~~

The command above is **DRY RUN ONLY**. After reviewing paths and preserving a separate consistent DB backup, the optional apply step is:

~~~powershell
py release-source/nexttoppersqr/qr-analytics-v3/INSTALL_QR_REPORTS_V3.py --app-root D:\timetable-intelligence-platform --apply
~~~

Apply backs up original routes.py, adds the isolated API hook and copies new reporting module, importer and web route. It refuses overwriting conflicting existing files. It does **not** restart API/web, touch Cloudflare KV/Worker, or alter QR images, targets, IDs or live DB tables. If Python compilation fails the installer restores routes.py.

**Not deployed or accepted yet.** Validate against a DB copy, run current Python tests and strict Next.js build, verify Sheets/Today/Weekly/Test Monitor and old printed QR fast redirects, then schedule an explicit controlled restart.

## Official download report import

Google: Play Console → Download reports → Statistics → installs country CSV (suffix _country.csv; often UTF-16). Apple: App Store Connect Analytics → App Store Downloads complete report (often tab-delimited gzipped text). Source references:
- https://support.google.com/googleplay/android-developer/answer/6135870
- https://developer.apple.com/documentation/AppStoreConnectAPI/downloading-analytics-reports
- https://developer.android.com/google/play/installreferrer

Set the reporting DB path **beside the active database.path** used by the API. The below path is an example only; do not guess if your active DB differs:

~~~powershell
py services\api\scripts\import_store_downloads_v3.py --store play --file "C:\Reports\installs_com.example.app_202610_country.csv" --app-id "com.example.app" --db "D:\timetable-intelligence-platform\data\qr_store_reports_v3.sqlite3"
py services\api\scripts\import_store_downloads_v3.py --store apple --file "C:\Reports\AppStoreDownloads.txt.gz" --app-id "1234567890" --db "D:\timetable-intelligence-platform\data\qr_store_reports_v3.sqlite3"
~~~

Never commit private publisher report data, production DBs, app API keys or secrets to GitHub.

## Production acceptance checklist

- Active database identified; SQLite integrity and critical non-QR + QR baseline row counts unchanged.
- Geographic and browser data tested on different countries/devices and Unknown cases.
- PDF/CSV links tested globally and for an individual QR; store data verified against official publisher reports.
- Reports unauthorized access assessed at existing admin access boundary.
- Backend regression, strict TypeScript/web build, backup/rollback, Cloudflare old printed QR performance tested.

**Status: review candidate only; no live app restart, deployment or store account connection has occurred.**
