# v1.0.18 QR Studio + International Analytics

This release replaces the technical/combined QR page with two clean mobile-ready tabs.

## QR Generator
- Any valid HTTP/HTTPS link can generate a QR.
- Only the link is required; the name is optional and is generated automatically when blank.
- The public tracking base is fixed internally to `https://nexttoppers.sagarkerhalkar.com`; it is not shown as a configuration field.
- Every new QR is stored and Active automatically.
- Preview after generation.
- Download as PNG, SVG or PDF.
- Test QR and Open Analytics actions.

## QR Analytics
- Global view and per-QR scope.
- Total human scans, approximate unique visitors, today, rolling 30 days, countries and active QR count.
- Animated 30-day trend chart.
- Country, device and browser analytics.
- Top-performing QR ranking.
- Searchable, paginated saved QR library.
- Activate / deactivate / reactivate.
- Clear Scan Data without deleting the QR.
- Delete QR permanently with its scan history.
- Re-download PNG/SVG/PDF and export CSV.

## Reliability changes
- Removes the external is.gd dependency from normal QR creation.
- QR tracking uses the compact stable route `/q/<7-character-code>`.
- Installer creates a temporary QR after startup and verifies: create, auto-activate, fixed public base, PNG/SVG/PDF, per-QR analytics, deactivate/reactivate, clear scan data and permanent delete. The temporary QR is removed before acceptance.
- Existing rollback, full backend tests, web regression tests, strict TypeScript, Next.js production build, all-tab smoke checks and Test Monitor performance checks remain mandatory.

Package SHA-256: `9f5838c6e38c0fe3a0324d2c803267d8610b886a95e7f7efd992120cbf255a49`

This remains a draft release candidate until the real Windows installer passes.