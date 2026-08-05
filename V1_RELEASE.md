# v1 Windows LAN release

Current repair package: `timetable-intelligence-platform-v1.0.1-weekly-notification-fix.zip`

SHA-256: `201174611162212467daf1ad347192ab69c1a74dea1425c3f3a077083262ca8d`

## v1.0.1 repairs

- Weekly Timetable no longer opens empty. The web page requested 500 records while the API accepted only 100, causing HTTP 422 and a false “No matching classes” screen.
- Weekly API now accepts up to 1000 verified timetable rows.
- The weekly screen selects today when classes exist; otherwise it selects the first day containing classes.
- Notification rules now have a Delete Rule action with confirmation.
- Deleting a rule also removes its delivery-test history.
- A guided Windows channel setup tool is included for Email, Google Chat, Telegram, WhatsApp provider webhook and Push webhook.

The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The repair package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
