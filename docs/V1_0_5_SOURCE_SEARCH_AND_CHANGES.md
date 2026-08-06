# v1.0.5 — source-wise search, transliteration and simple Sheet Updates

## Added Google Sheets

Every connected workbook is profiled tab by tab. Official timetable workbooks use their dedicated verified parsers. Other workbooks use a generic header-driven parser that reads common columns such as Course, Class, Subject, Chapter, Topic, Teacher/Made by, Link, PDF and Status.

The supplied `Test Series - 2026` workbook is treated as a test/learning-file library, not as a timetable. Its 10 tabs and 780 linked files are indexed.

## Search

Search supports:

- Google Sheet filter;
- tab filter after choosing a Google Sheet;
- videos, PDFs, tests/documents and presentations;
- English, Hindi and Sanskrit source text;
- local Devanagari-to-Roman search expansion, e.g. `kabir` finds `कबीर`;
- partial, alias and common misspelling matching;
- automatic indexing of newly connected Sheets.

## Notifications

Each class is displayed as a clear path:

`Stream → Class → Batch → Subject`

The next line shows the complete lesson/topic. Nirmaan variants such as New NCERT, Old NCERT and Nirmaan 2.0 remain visible.

## Sheet Updates

Cell-level edits are grouped by Sheet row and sync check. Normal users see one sentence describing what was added, changed or removed, where it happened, and how it affects the app. Earlier/new values and technical coordinates remain available under an expandable detail section.
