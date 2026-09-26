# QR Platform Architecture

## Navigation

`New QR -> Templates -> Bulk Create -> My QR Codes -> Analytics`

Only the exact/most-specific route may be active in navigation.

## QR campaign

Every saved QR is an independent campaign with its own:
- UUID/ID;
- compact public slug;
- target/action content;
- tracking mode;
- identity mode;
- design snapshot;
- scan-screen snapshot;
- template provenance (optional);
- scan events and analytics.

A template is a design/settings source, not a shared analytics bucket.

## Templates

`qr_templates` persists reusable branding/settings on the server so templates work across browsers/devices.

A template includes QR design + scan-screen experience + tracking/identity defaults.

Creating a QR copies a snapshot of the template settings into that QR. Later template edits do not silently mutate already-issued/printed QR campaigns.

Deleting a template detaches provenance but preserves QRs and their analytics.

## Bulk creation

Endpoint: `POST /api/v1/qr-bulk`

Input:
- `template_id`
- `items[]` with `name` and `url`

Rules:
- 1-500 rows;
- template must exist;
- Bulk analytics mode requires a Tracked template;
- duplicate names in one request are rejected;
- every row receives a unique ID/slug.

Bulk UI supports manual rows, pasted spreadsheet/CSV text and CSV/TXT file import.

## Per-QR analytics

Endpoint: `GET /api/v1/qr-analytics?qr_id=<QR_ID>`

Bulk QRs never share scan totals merely because they share one template.

Regression contract:
- scan QR A once -> A total = 1;
- do not scan QR B -> B total = 0.

## Verified scan lifecycle

Tracked public scan route renders the branded experience first. Browser confirmation records the verified event and then continues to the destination/action.

Primary analytics distinguish:
- verified scans;
- anonymous unique browsers/devices;
- legacy/unverified events;
- bots/previews;
- Exact/Detected/Unknown source attribution.

## Shared assets

Uploaded logos/full-screen images can be referenced by templates and QR campaigns. Asset deletion is reference-aware: an asset must not be physically removed while another template or QR still uses it.

## Wi-Fi

- Direct Wi-Fi QR embeds the Wi-Fi payload for the OS/scanner Join Network experience.
- Tracked Wi-Fi collects analytics/identity first and then provides the connection helper; a normal webpage cannot universally force silent Wi-Fi joining after tracking.

## Release safety

The Windows release installer:
1. stops only this app;
2. backs up exact changed files, databases and web build;
3. applies release payload;
4. runs complete backend tests;
5. runs web regression tests;
6. runs strict TypeScript;
7. builds Next.js production output;
8. starts isolated API/web ports;
9. smoke-tests every main page;
10. executes QR lifecycle + template/bulk/per-QR analytics runtime checks;
11. checks existing timetable/Test Monitor/Sheet Updates contracts;
12. rolls back on any failure.
