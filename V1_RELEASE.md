# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.10.3-slow-sync-fix.zip`

SHA-256: `bc4523bec67f6654e18711ffcfa0b0663a9bfb46ed2282c7c47602b4f1f6d929`

## v1.0.10.3 slow Google Sheet sync repair

- Reapplies the complete reliable hyperlink Search, Google Sheet manager, professional Test Analysis, notification guidance and understandable Change History update after v1.0.10.2 rolled back.
- v1.0.10.2 failed because Commerce did not complete inside the installer’s fixed 12-minute validation window; this was a slow live sync, not a code or Sheet-format error.
- The installer starts in controlled validation mode with automatic all-source refresh temporarily disabled.
- `YT Science 2026-27` and `Test Series - 2026` are refreshed and validated first, with live progress and up to 30 minutes per required source.
- The app is then restarted in normal automatic-refresh mode and Commerce, Humanities, Science, Nirmaan and other connected workbooks are queued in the background.
- A slow non-critical workbook no longer rolls back the already validated Search and UI update.
- YT Science Class 12 must expose at least 70 indexed records before success; Test Series must expose at least 700 structured tests.
- A visible `Installed build: v1.0.10.3` label is shown in the sidebar, and API health reports version `1.0.10.3`.
- Automated validation: 63 backend tests passed; 41 TypeScript/TSX files parsed with zero syntax errors; Python compilation and ZIP integrity passed.
- Existing database, connected Google Sheets, notification rules and isolated ports remain preserved. Port 3457 remains protected.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes credentials, recipients, logs, runtime files and backups.
