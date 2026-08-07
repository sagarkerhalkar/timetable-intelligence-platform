# Timetable Intelligence Platform v1

This branch is reserved for the stable Windows LAN build running at `http://156.156.40.51:3500`.

Current release candidate: **v1.0.13 fast navigation**.

## Locked refresh schedule

- Google Sheets: every 30 minutes
- Visible pages: every 5 minutes and when the browser tab regains focus
- Notification scheduler: every 1 minute

## Current v1 behaviour

- Today timetable retained with one-click Commerce, Science, Humanities and Nirmaan stream-wise navigation.
- Simplified selected-day and weekly timetable views.
- Fast multilingual indexed Search.
- Human-readable Sheet Updates with logical row/field grouping and clickable changed links.
- Sunday Test Readiness: Monday-Saturday Sheet Test Dates belong to the same week's Sunday while the original Sheet date remains visible.
- Test Monitor source tabs use lightweight SQL counts, direct indexed sheet filtering and immediate first-click feedback.
- Notification send time, weekday, minutes-before, Test now, channel readiness and delivery history remain available.
- Port 3457 is protected.

## Public repository boundary

No database, credentials, recipient list, Google Sheet data, logs, runtime files or backups may be committed to this public repository.
