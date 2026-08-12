# v1.0.20 International QR Platform

This draft records the v1.0.20 Windows release candidate. The installer package remains the authoritative cumulative runtime payload; stable `v1` is not changed until the real Windows acceptance run passes.

## Why
The 12 Aug recording showed multiple QR routes visually active at the same time. v1.0.20 fixes navigation at the route-matching level and expands the QR product to the full requested commercial workflow.

## Navigation
- `/qr` -> only QR Generator active
- `/qr/codes` -> only My QR Codes active
- `/qr/stats` -> only QR Analytics active
- immediate pending state + prefetch for smoother clicks
- regression test added for route selection

## QR design
- Dots: square / rounded / dots
- Marker border: square / rounded / circle
- Marker center: square / rounded / circle
- independent QR/background/marker-border/marker-center colors
- QR logo upload and scan-safe size slider
- optional white logo safety plate
- frame none/text/badge with CTA
- PNG/SVG/PDF

## Scan screen
- branded animated loader, uploaded logo screen, or uploaded full-page image
- logo size control
- full-page image size + contain/cover
- accent/background + redirect delay
- mobile/tablet/landscape/safe-area/reduced-motion handling

## Verified analytics
Main KPIs require browser confirmation; simple preview/server fetches do not inflate verified totals. Duplicate event IDs are ignored. Legacy direct redirects remain separate.

Metrics include verified total scans, unique browsers/devices, today/7d/30d, countries, device, OS, browser, source platform, confidence, trend and recent scans.

## Source attribution
Exact when a channel-tagged QR variant is distributed; otherwise Detected or Direct/Unknown is reported when apps strip referrer/source signals. Supported tags include WhatsApp, Telegram, Instagram, Google Chat, Web, Facebook, Messenger, LinkedIn, Email, Teams, Slack and Discord.

## Accuracy boundary
Without login/identity, no anonymous QR product can prove a real person across multiple browsers/devices. v1.0.20 therefore reports Unique Browsers/Devices rather than claiming false person-level precision.

Package SHA-256: `c17be1d7b595b9bf985fde7d0473e19f240a65ca9c13a4703d02eb8fd49b4a8a`
