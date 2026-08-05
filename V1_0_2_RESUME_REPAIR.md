# v1.0.2 Resume Repair

Fixes the Windows installer failure `Cannot overwrite ... SETUP_NOTIFICATION_CHANNELS_WINDOWS.ps1 with itself` when the update ZIP is extracted directly inside `D:\timetable-intelligence-platform`.

The installer now compares canonical source and destination paths and skips same-file copies. It then continues backend tests, TypeScript validation, Next.js production build, startup, and health checks.

Package: `timetable-intelligence-platform-v1.0.2-resume-repair.zip`

SHA-256: `0be65cca35a73c848b4dfbf19f3cd14830f5162fb70f978e4d23791a7ae9a96b`

No database, Google Sheet connection, notification rule, LAN port, or port 3457 configuration is changed.