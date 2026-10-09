# QR Insights — isolated read-only proof (9 October 2026)

This is an isolated candidate branch; **no production change, no merge, no Worker deployment, no database migration**.

## Included
- Read-only SQLite reporter for verified non-bot QR activity.
- Country, state/region, city, and district if actually captured; otherwise Unknown.
- Device type, operating system and browser, plus per-QR pseudonymous repeat-device counts.
- CSV exports and PDF report.
- Google Play / Apple App Store QR scan totals. **These do not equal confirmed installs.**
- Offline full-feature candidate and synthetic tests are supplied separately.

## Existing system and safety
The QR Worker already supplies country/region/city in verified scan telemetry. This candidate does not touch QR creation, editing, destination links or edge KV.
Read **docs/CURRENT_PROJECT_CONTEXT.md** before any runtime activity. Historical divergent databases exist. The authoritative database path is:
D:\timetable-intelligence-platform\services\api\data\timetable.db

## Invocation — first run against verified offline copy
~~~powershell
py -m pip install "reportlab>=4.0"
py .\qr_insights.py --database "D:\path\to\verified\offline\copy\timetable.db" --output-dir "D:\qr-insights-export"
~~~

## Mandatory production acceptance before live integration
1. Verify exact currently running Windows source and database; current GitHub main is not the full runtime.
2. Snapshot database and keep checked backup. Compare pre/post counts.
3. Validate reports, timezones and location metadata against real data, in staging.
4. Implement authenticated, paginated admin dashboard integration only after tests.
5. For **actual installs**, integrate authenticated Play Console and App Store Connect attribution exports/API where supported. Pre-existing direct QR scans cannot retrospectively prove installs.
6. Test and roll back on staging before any authorized production deployment.

**Status:** isolated code candidate only; no live testing or production deployment has been performed.
