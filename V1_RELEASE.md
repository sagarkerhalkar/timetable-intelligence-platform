# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.7-test-monitor-search-fix.zip`

SHA-256: `75d3c29cd64d5bf890cfcbc9cfbbdc8d845fe5c5746be961855ddd53860eb2b6`

## v1.0.7 structured Test Series search and Test Monitor

- `Test Series - 2026` is parsed as a structured test-operation workbook instead of a generic list of links.
- Search indexes Google Sheet, tab, course, class, subject, chapter, topic, creator, file name, App Status, Test Date, Result Dashboard and Video Solution Update.
- Google Sheet and tab filters continue to work as new sources are connected.
- Romanised English queries are stored with the original Indic text; for example, `kabir` finds `कबीर के दोहे` in `Nirman 2026`.
- The Test Monitor shows App Status for `PRARAMBH 2026` and `Nirman 2026`, and Result Dashboard / Video Solution for due tests in `PRARAMBH 2026`.
- One setup form creates four alerts: new test after each successful 30-minute Sheet check, Sunday App Status, Monday 5:00 PM Result Dashboard and Tuesday 5:00 PM Video Solution. Times are editable.
- The first successful scan is a baseline, so hundreds of historical tests are not falsely reported as newly added.
- Live snapshot validation found 754 structured test records and 802 searchable file entries across 10 tabs.
- The Windows installer runs 58 backend tests, TypeScript validation, the full Next.js production build, live Test Series sync and final API/page checks before reporting success.

The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The release package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
