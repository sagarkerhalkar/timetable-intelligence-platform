# v1.0.24 — Reusable QR Templates, Bulk Creation and Per-QR Analytics

Status: **release candidate — Windows acceptance required before merge to stable `v1`.**

## User requirement

Configure logo, full-screen scan image, colors, QR style, scan-screen experience, tracking and identity settings once, save multiple named templates, then create many QRs by entering only Name + URL. Every generated QR must remain separately analyzable.

## Implemented

### Multiple templates

Server-side CRUD:
- list/get/create/update/duplicate/delete;
- one default template at a time;
- template usage count;
- existing QR campaigns survive template deletion.

### Bulk QR Generator

- choose a template;
- manual Name + URL rows;
- spreadsheet/tab-separated paste;
- CSV paste;
- CSV/TXT upload;
- up to 500 rows/request;
- Generate All;
- result actions include PNG and individual Analytics links.

Bulk creation requires a Tracked template because the requested workflow requires analytics for every generated QR.

### Independent analytics

Every bulk-created QR receives a distinct ID and slug. The analytics API remains scoped by QR ID.

Regression test explicitly proves scans on QR A do not change QR B.

### Template provenance

A QR response can include `template_id` and `template_name`. This is provenance only; design/experience are copied into the QR record so later template changes do not unexpectedly change existing campaigns.

### Asset safety

Shared uploaded logos/backgrounds are reference-counted across both QRs and templates before cleanup.

## Database changes

- `qr_codes.template_id`
- new `qr_templates` table
- migration creates the new column before indexes that depend on it.

## API additions

- `GET /api/v1/qr-templates`
- `GET /api/v1/qr-templates/{id}`
- `POST /api/v1/qr-templates`
- `PATCH /api/v1/qr-templates/{id}`
- `POST /api/v1/qr-templates/{id}/duplicate`
- `DELETE /api/v1/qr-templates/{id}`
- `POST /api/v1/qr-bulk`

## Frontend additions

- `/qr/templates`
- `/qr/bulk`
- New QR can load `?template=<id>`
- My QR Codes shows template provenance and per-QR analytics action.

## Acceptance gate

The release installer creates a temporary template, bulk-creates A and B, records one verified scan only on A, checks A=1/B=0, deletes the template, proves QR A still exists unchanged, then cleans temporary records.
