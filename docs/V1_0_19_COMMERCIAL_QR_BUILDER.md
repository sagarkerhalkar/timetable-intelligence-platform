# v1.0.19 Commercial QR Builder

This release replaces the confusing combined QR screen with a commercial product workflow inspired by established QR platforms while keeping Daily Timetable branding and only the Website/Link QR type.

## Pages

- New QR: 3-step builder — Content, Scan Screen, Design.
- My QR Codes: searchable/filterable management table with edit, activate/deactivate, clear scan data, permanent delete, and PNG/SVG/PDF downloads.
- Stats: total scans, approximate unique visitors, today/30-day activity, countries, devices, browsers, animated trend/rankings, top campaigns, recent scans, CSV export, global or per-QR scope.

## Branded scan experience

The public `/q/<slug>` route no longer produces a blank white redirect flash. It records the scan and immediately renders one of:

- branded animated loader;
- uploaded logo screen;
- uploaded full-screen image page.

It then redirects automatically to the saved destination. Redirect display duration is configurable in the builder.

## QR design

- foreground/background colors;
- optional frame/CTA text;
- optional center logo;
- live preview;
- PNG, SVG, PDF.

Uploaded PNG/JPG/WEBP assets are sanitized with Pillow. The public tracking base remains fixed to `https://nexttoppers.sagarkerhalkar.com` and is not exposed as a setup field in the builder.

## Dynamic management

Destination, name, QR design and scan experience can be edited while preserving the same seven-character public slug. Every new QR starts Active automatically.

## Validation

- targeted QR API regression suite: 10/10 passed in local harness;
- Python syntax checks passed;
- TS/TSX transpilation checks passed;
- Windows installer still runs full backend tests, web regression tests, strict TypeScript, Next.js production build, all-tab smoke checks and QR lifecycle validation before acceptance.

Package SHA-256: `c819c5b54b3d9569d2116e9f8170d74da15195114cb5fe5e4a8809ba7ca9fe8f`
