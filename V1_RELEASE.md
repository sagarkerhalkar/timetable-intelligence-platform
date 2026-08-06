# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.9-self-explaining-sheets.zip`

SHA-256: `ac8583992c11d4b4b9ccd7dc8ed90a723a2a75104467bae2821b6fc50dfe7491`

## v1.0.9 self-explaining Google Sheets

- Newly connected Google Sheets are profiled tab by tab instead of silently assuming that every workbook uses the same structure.
- Each non-empty tab shows `Ready for Search` or the exact missing headings/structure that must be corrected.
- Generic heading-driven indexing understands Course/Batch, Class, Subject, Chapter/Topic, Teacher/Made by, Docs/PDF/Video/PPT/Sheet links, App Status, Test Date, Result Dashboard and Video Solution Update.
- Official Commerce, Science, Humanities and Nirmaan timetable workbooks continue to use their dedicated verified timetable parsers.
- Search supports all sources, one Google Sheet, one tab, stream and file-type filters, plus Hindi/Sanskrit and Roman-keyboard forms such as `kabir` → `कबीर`.
- Google Sheets now has `Remove Sheet`, which removes only the local connection and locally derived data. It never deletes the original Google Sheet.
- Test Analysis separates completed, remaining, future and data-quality problems in plain language.
- Change History separates Added, Changed and Removed, groups row edits, and shows Before → After values while keeping cell coordinates under admin details.
- Automated validation: 61 backend tests passed and 44 TypeScript/TSX source files parsed with zero syntax diagnostics. The Windows installer still requires the real TypeScript check and complete Next.js production build before starting the app.
- The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The release package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
