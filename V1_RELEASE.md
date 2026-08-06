# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.10-reliable-search-admin-ui.zip`

SHA-256: `42ea95b73a09adca1431f9985536f558fad9cf2e8628d75ff89478e1ad29488b`

## v1.0.10 reliable hyperlink Search and clearer administration

- Generic Google Sheet indexing now scans actual hyperlinks and URLs in every physical column. A valid link is no longer ignored because its heading is `Remarks`, `Output`, `Raw` or another custom name.
- Live validation of `YT Science 2026-27` found 81 structured Class 11 links and 77 Class 12 links. Class 12 uses `Remarks` for its YouTube-link column.
- Search shows the exact indexed count for the selected Google Sheet and tab, plus workbook/tab provenance, class, subject and teacher details.
- Google Sheets has a prominent Manage connected Google Sheets section with Open, Check and Remove actions. Remove affects only local indexed data, never the original Sheet.
- Test Analysis adds an overall readiness percentage, clickable-file coverage, dated-test coverage, new-this-week totals, and subject/class/course analytics.
- Notifications now clearly explains Personal WhatsApp, Telegram person/group chat IDs, Google Chat Spaces and Email, including configured/not-configured status and the exact Windows setup command.
- Personal WhatsApp can target one fixed person or allow the user to choose a person/group when WhatsApp opens.
- Change History hides raw row/cell numbers from the normal view and states the exact field changed with Before and After values. Technical coordinates remain admin-only.
- Automated validation: 63 backend tests passed; 41 TypeScript/TSX files passed syntax validation. The Windows installer requires the real TypeScript check and complete Next.js production build before starting.
- The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The release package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
