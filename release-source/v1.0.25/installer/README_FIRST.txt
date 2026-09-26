Timetable Intelligence Platform v1.0.25
Paged UX + Larger QR Library

TARGET
  D:\timetable-intelligence-platform
  Web 3500
  API 3550
  Port 3457 is protected and is never touched.

WHAT CHANGES
  My QR Codes: 8 large cards/page, actual QR preview, Show QR, Copy Source Link,
  Copy QR Link, cross-page checkbox selection, Select this page, Clear selection,
  Delete Selected, and all existing Analytics/Edit/PNG/SVG/PDF/channel/status/
  clear-data/delete actions.

  Templates: search + 6/page.
  Bulk: templates 6/page, Name+URL input 10/page, results 10/page.
  Analytics: Device Intelligence 6/page, Recent verified scans 15/page.

WHAT DOES NOT CHANGE
  Existing QR analytics semantics, Wi-Fi behavior, identity behavior, QR types,
  template/shared-asset safety, timetable, Test Monitor, Sheet Updates,
  notifications or Google Sheet parsing.

HOW TO RUN
  1. Extract this ZIP on the Windows server.
  2. Double-click RUN_V1_0_25_NOW.cmd
  3. The installer creates a timestamped backup before replacing files.
  4. It runs backend tests, web tests, real TypeScript typecheck, Next.js build,
     restarts only ports 3500/3550, smoke-tests QR pages and existing Timetable/
     Sheet Updates/Test Monitor APIs, then runs a temporary QR template/bulk/
     independent-analytics lifecycle probe.
  5. Any failure after apply triggers rollback.

IMPORTANT
  Do not merge PR #12 into stable v1 until this real Windows acceptance finishes
  without rollback.
