# v1.0.13 fast navigation and one-click filters

## User-reported problems

1. The Today page showed Commerce, Science, Humanities and Nirmaan counts, but the cards were plain text and could not open a stream-wise timetable.
2. In Test Monitor, selecting tabs such as `PRARAMBH 2026` or `Nirman 2026` appeared to ignore the first click and could take too long. Users clicked repeatedly because the selected state did not change until the server response finished.

## Corrections

### Today stream navigation

- Commerce, Science, Humanities and Nirmaan are now real one-click links.
- Each card opens the exact current-day timetable with both `date` and `stream` filters.
- The entire card is clickable, keyboard accessible and has a visible hover/focus state.
- Existing Today totals and the universal timetable remain unchanged.

### Test Monitor one-click navigation

- The clicked tab becomes visually active immediately, before the server response returns.
- The selected tab is protected from repeated clicks while that navigation is already in progress.
- The loading line explicitly confirms that the click was accepted.
- Navigation preserves the current scroll position instead of bouncing the user around the page.

### Test Monitor performance

The previous selected-tab render performed two Test Monitor analytics calls: one complete payload for tab counts, followed by another complete payload for the selected tab. The backend also loaded all Test Series records before filtering the selected tab in Python.

v1.0.13 changes this to:

- one Test Monitor analytics request for the currently selected tab;
- direct SQLite filtering by `sheet_name` through the existing `test_records(source_id, sheet_name)` index;
- a new lightweight `/api/v1/test-monitor/tabs` endpoint using SQL `GROUP BY` counts instead of constructing every `TestRecord` only to show the tab bar;
- source metadata remains a small parallel request.

## Preserved requirements

- v1.0.12 human-readable Sheet Updates grouping remains in place.
- Changed Sheet URLs remain directly clickable.
- Monday-Saturday Test Dates still belong to the same week's Sunday cycle while the original Sheet date remains visible.
- Strict TypeScript settings remain enabled, including the v1.0.11.1 `cellParts()` safety fix.
- Port 3457 remains protected.
- Existing databases, connected Google Sheets, notification rules and runtime configuration are backed up and preserved by the Windows installer.

## Package

`timetable-intelligence-platform-v1.0.13-fast-navigation.zip`

SHA-256: `fdbb8b647c4e238be4c0238959cdf5cf9bc972e9976359f9ed2d670bac30fcbe`
