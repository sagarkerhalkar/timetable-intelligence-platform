# QR 5wqrrpw urgent same-QR link change

Date: 2026-09-26
Branch: nexttoppersqr

## Incident
Public QR slug `5wqrrpw` continued opening the previous YouTube target even after the user changed the destination in the app.

Old target: `https://www.youtube.com/watch?v=TmrkmcY9flc`
Requested target: `https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`

## Root cause identified
The earlier urgent V4 helper was hard-coded for QR slug `smfffdy`, so it could never update local/edge state for `5wqrrpw`.

The QR architecture has two relevant states for a tracked QR:
1. local QR record `target_url`
2. Cloudflare KV route `qr:<slug>`

If only one side is updated, the printed QR can continue opening the stale destination.

## V5 repair package
Package: `NEXTTOPPERS_UNIVERSAL_SAME_QR_LINK_CHANGER_V5.zip`
SHA-256: `080e189bf8220b9616cf8485548dfc10b1a2c2b6535d7de5d4db872d459eadca`

V5 is generic. It accepts any tracked NextToppers QR URL/slug, preserves the same QR id/slug, updates the local target, updates exactly the matching Cloudflare KV key, reads both back, and waits for public-edge propagation before reporting success.

Urgent defaults:
- QR: `https://q.nexttoppers.workers.dev/q/5wqrrpw`
- Target: `https://www.youtube.com/watch?v=Wcb3ZPnZ5Rk`

## Safety scope
V5 does not regenerate the QR, restart web/API, deploy Worker code, rotate Worker secrets, touch Sheets/Timetable/Test Monitor, or modify other QR KV keys.

## Acceptance
The run is accepted only when:
- local QR read-back shows requested target
- QR id and slug are unchanged
- Cloudflare KV `qr:5wqrrpw` read-back shows requested target and `active=true`
- public QR exposes the requested target after edge propagation

Windows production acceptance is pending the user's real server run.