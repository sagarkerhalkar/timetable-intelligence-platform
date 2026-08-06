# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.8-installer-count-fix.zip`

SHA-256: `41c9f1f361aa601d8c6e2c7126ffa8832efa8910f8e1707a1aa1bf2f75e22712`

## v1.0.8 installer validation repair

- Reapplies the complete v1.0.7 structured Test Series Search and Test Monitor update after the automatic rollback.
- Fixes a PowerShell StrictMode validation error when `kabir` returned exactly one correct result.
- The installer now converts zero, one or many filtered search results into a real array before checking `.Count`.
- Preserves the SQLite database, connected Google Sheets, notification rules and isolated ports.
- Continues to run 58 backend tests, TypeScript validation, the full Next.js production build, live Test Series sync and final API/page checks before reporting success.
- The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The release package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
