# 2026-08-13 - QR Scale v2 handoff

User approved proceeding with QR Scale + Analytics v2.

Locked requirements:
- preserve existing timetable, Google Sheet, test, change and QR records;
- keep GitHub current in the same development turn;
- record meaningful actions, errors, root cause, fixes and PASS results;
- keep replies and code delivery quick;
- My QR Codes must support lakhs of QR records with compact server-side search/filter/sort/paging;
- Analytics must be redesigned for approximately 10,000,000 accesses/scans using scalable summaries rather than loading all raw events;
- every QR must provide Copy Source Link, Copy Public QR Link and Open/Show QR anytime;
- existing QR template, bulk, design, identity, verified-scan, analytics and lifecycle behavior must remain compatible.

Authoritative runtime DB remains:
`D:\timetable-intelligence-platform\services\api\data\timetable.db`

Known recovered baseline from this session:
- sources 4
- timetable_entries 989
- test_records 1122
- changes 95
- qr_codes 24
- qr_scans 24

Before the next Windows release changes runtime, record the current database identity/counts and make a verified local backup. After the release, verify the same data and verify Today, Weekly, Google Sheets, Sheet Updates, Test Monitor and QR together.

Process update:
- PASS: created `docs/FAST_SAFE_QR_V2_DEVELOPMENT_POLICY.md` in commit `84a30e00e81719fe93dffbe69cfe7c964809e02e`.
- FAIL: a larger replacement edit of the existing mandatory handoff policy was blocked by the connector before it was applied.
- FIX/PASS: the dedicated mandatory policy file was created successfully instead of spending more time retrying the blocked write.

Next action: implement QR Scale + Analytics v2 against isolated test data first, then package cumulatively and verify the production data baseline before and after Windows acceptance.
