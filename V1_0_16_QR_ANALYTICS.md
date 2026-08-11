# Timetable Intelligence v1.0.16 — Google Forms QR Analytics

## New tab

Adds **QR Analytics** to the main navigation.

Operators can create a named QR for a Google Form, download PNG, copy the tracked link, open the original form, disable/re-enable tracking, export CSV, and review scan analytics.

## Tracking architecture

The QR encodes `<PUBLIC-BASE>/backend/api/v1/qr/scan/<slug>` rather than the Google Form directly. The scan is recorded in Timetable Intelligence and then immediately redirected to the Google Form.

Stored analytics include total human scans, approximate unique anonymous browsers, scan time, country code when supplied by Cloudflare/supported proxy headers, device class, browser family, bot/preview count, and recent scan history. Raw IP addresses and Google Form responses are not stored.

## Worldwide requirement

The current LAN app address is not reachable worldwide. Worldwide tracking requires a public HTTPS base URL/domain/tunnel that routes `/backend` to the application. Cloudflare-proxied traffic can supply `CF-IPCountry`, which is used automatically for country analytics.

## Validation and installer gate

- QR SQLite schema/database smoke passed.
- QR PNG generation smoke passed.
- New QR page passed strict TypeScript fixture with `strict` and `noUncheckedIndexedAccess`.
- Installer must still pass the full backend suite including QR route tests, web regression tests, strict TypeScript, full Next.js build, all existing main-page smoke checks, `/qr`, QR list/analytics APIs, and Test Monitor cached-tab timing before accepting the release.
- Rollback protection for changed files, both databases and `.next` remains active.

Package SHA-256: `c5e09b0d22078389d40c830e15f1754d95f04623f0c9ecb152668872a879bc09`
