# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.5-source-search-update.zip`

SHA-256: `234d68df3d1f056822109cce2e658bb71ea400e184888e9566bebe660d618d6d`

## v1.0.5 source-wise search and simple Sheet Updates

- Search can be restricted to one connected Google Sheet and then one tab.
- Search indexes videos, PDFs, tests/documents, presentations, spreadsheets and other learning links.
- A local Hindi/Sanskrit transliteration index allows normal English-keyboard queries such as `kabir` to find `कबीर`; no online translation service is used.
- Newly connected content/test Sheets use a generic header-driven parser for Course, Class, Subject, Chapter/Topic, Teacher/Made by, file link and status columns. Official timetable workbooks continue to use their dedicated verified parsers.
- The supplied `Test Series - 2026` workbook was audited: 10 tabs and 780 searchable files, including 751 documents/test papers and 26 PDFs.
- Notification messages now show `Stream → Class → Batch → Subject`, followed by the full lesson/topic. Nirmaan variants such as New NCERT, Old NCERT and Nirmaan 2.0 remain visible.
- Sheet Updates combines several changed cells from the same row into one plain-language story. Technical coordinates remain hidden under an admin detail section.
- The installer connects `Test Series - 2026` when needed, rebuilds the multilingual index, runs 53 backend tests, requires TypeScript and Next.js production builds, and restores the previous database/files if validation fails.

Live-copy audit totals across five workbooks: 81 tabs, 930 timetable entries and 4,315 searchable files.

The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The release package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
