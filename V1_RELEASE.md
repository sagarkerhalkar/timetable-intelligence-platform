# v1 Windows LAN release

Current repair package: `timetable-intelligence-platform-v1.0.4-full-data-fix.zip`

SHA-256: `ffdbae77bbaf35e061d1e045b5f4ac0794212bdc8d12ef5867d3586969a05426`

## v1.0.4 full live-data reconciliation

- Commerce now reads both `Weekly Planner` and `Time Table/Planner`. The dated Commerce planner ends on 2 August 2026, so the active repeating timetable is used for the current week and the missing topic is clearly marked pending rather than invented.
- Nirmaan Old NCERT preserves both physical subject columns under the merged 6:00 PM heading. The final API must contain Science and Mathematics at 6:00 PM before the Windows installer reports success.
- Science Mathematics/Biology option cells are split into separate simultaneous classes.
- All 71 current workbook tabs and all populated/hyperlinked cells are audited for timetable and content extraction.
- Learning-content totals exclude OTP, uploader, status and admin-only links; `Vidoe Drive Link` is recognized as video; Canva/PPT links are presentations.
- Live audited totals: 930 timetable entries and 3,535 searchable learning links (1,825 videos, 1,642 PDFs, 62 presentations and 6 other learning links).
- For 5 August 2026 the verified Today result is 20 classes: Commerce 6, Science 4, Humanities 4 and Nirmaan 6.
- Notifications use a three-step form. Personal WhatsApp requires no Business account: the app prepares the message, the user opens WhatsApp and presses Send. Every saved rule has Test and Delete actions.
- The installer force-syncs all four Sheets and validates the final SQLite/API data, not only parser output.

The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The repair package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
