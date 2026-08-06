# v1.0.9 — Self-explaining Google Sheets

This release removes the assumption that every new Google Sheet must be manually coded first.

When a workbook is connected, the app reads every visible and hidden tab, searches the first rows for a real heading row, identifies column meanings from headings rather than fixed column letters, and shows what it understood for each tab.

## Automatically understood headings

- Course / Batch / Programme
- Stream
- Class / Grade / Standard
- Subject
- Chapter Number
- Chapter Name / Topic / Lesson / Test Name / Title
- Teacher / Faculty / Made by / Prepared by
- Docs, PDF, Video, YouTube, Presentation, PPT, Canva, Spreadsheet and Excel links
- App Status
- Test Date
- Result Dashboard
- Video Solution Update
- Questions, duration, marks and remarks

Column order does not matter and common spelling variations are accepted.

## Search readiness

A non-empty tab is marked **Ready for Search** when it has a useful identity field and either a file/link field or operational test fields. A tab that is not ready displays its detected heading row, understood fields, indexed count, missing recommended headings and a plain-language warning.

## Removing a Sheet

**Remove Sheet** deletes only the local connection, local search index, derived timetable/test data and related local history. It never edits or deletes the original Google Sheet.

## Search

Search supports all connected workbooks, one Sheet, one tab, stream and file type. It searches English, Hindi and Sanskrit plus Roman-keyboard forms such as `kabir` for `कबीर`.

## Test Analysis

Test Analysis separates completed work, remaining work, future tests and data-quality problems that block reliable search or notifications.

## Change History

The first successful check becomes the baseline. Later checks group cell edits by workbook, tab and row and display:

- **Added** — a new row or value was added.
- **Changed** — an existing field changed, with Before and After values.
- **Removed** — a row or value was removed.

Technical cell coordinates remain hidden under admin details.

## Honest limitation

A completely unstructured Sheet with no headings, decorative merged text only, or unrelated tables mixed in the same region cannot be understood reliably. In that case the app does not guess; it shows the exact heading or structure that needs correction.
