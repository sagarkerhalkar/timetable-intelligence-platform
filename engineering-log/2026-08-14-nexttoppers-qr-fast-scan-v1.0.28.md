# 2026-08-14 — NextToppers QR fast-scan v1.0.28

## User-reported production issue

New tracked QRs now use the confirmed Cloudflare Worker hostname `https://q.nexttoppers.workers.dev/`, but scan-to-destination transition is taking about **7 seconds**, which is not acceptable for normal QR use.

## Evidence / cause

The recovered runtime source shows that tracked QR scan experiences intentionally carry an action delay (default 900 ms, minimum normalized to 650 ms). That configured delay alone does not explain ~7 seconds.

The larger avoidable cost is the current architecture: the Worker proxies the normal `/q/<slug>` web route, which requires the complete web scan experience before redirecting. This adds a full web/Next.js path and origin/tunnel work before the destination opens.

## v1.0.28 correction

Normal Worker scans move to a lightweight edge path:

`phone -> q.nexttoppers.workers.dev/q/<slug> -> lightweight qr-fast resolver -> tiny Worker scan experience -> destination`

A new backend router performs a direct indexed `qr_codes.slug` lookup and deliberately does **not** run the aggregate scan-count join used by the normal `get_qr_code_by_slug()` model path.

Browser-confirmation telemetry is posted to a same-origin Worker beacon endpoint. The Worker queues the analytics API subrequest with `ctx.waitUntil()` so analytics completion does not block the user-facing redirect path.

The tiny Worker page preserves:

- dynamic destination lookup;
- active/inactive enforcement;
- tracked/direct mode;
- anonymous persistent browser ID;
- verified browser scan event;
- country/Cloudflare edge metadata;
- browser, OS, device class, language, timezone, referrer/source and screen telemetry;
- email-identification mode;
- brand/logo/full-page experience;
- uploaded scan-experience assets through a Worker asset proxy;
- existing configured action delay (the expensive full Next.js scan bundle is what is removed).

The Worker keeps the current public hostname `q.nexttoppers.workers.dev`. Its API origin uses the existing `/backend` bridge, not the old `/q/<slug>` web path. This also means a future old-domain `/q/*` Single Redirect to the Worker is loop-safe without Worker-only filter fields.

## Changed payload files

- `payload/services/api/app/api/qr_fast.py`
- API `app/main.py` is patched by installer only to import/include `qr_fast_router`
- `worker/src/index.js`
- `worker/wrangler.jsonc` (`name=q`, Workers.dev on, Smart Placement on, API base through existing backend bridge)
- guarded Windows installer, DB guard, main patcher and one-click CMD runner

## Safety / validation contract

- production SQLite schema/rows are not migrated, deleted or replaced;
- read-only integrity/count guard before and after;
- backend full pytest suite runs against isolated temporary DB before runtime switch;
- Python compile and Worker `node --check` are blocking;
- only API port 3550 is restarted after validation;
- web 3500 is not stopped;
- protected dev port 3457 is never touched;
- public `/backend` qr-fast health must pass before Worker deployment;
- Worker `q` deployment is verified by build marker and an existing active tracked QR smoke request;
- if post-deployment Worker acceptance fails, installer attempts `wrangler rollback` to the previous `q` version, restores API source, and restarts the prior API.

## Package

`NEXTTOPPERS_QR_FAST_SCAN_V1_0_28.zip`

SHA-256: `690335570a83a009b9f4237f669e7e9681241a495dd0bf8191f1347398d42a06`

ZIP CRC: PASS.

## Acceptance status

Local package construction, Python source compile, Worker JavaScript syntax check, manifest generation and ZIP CRC passed.

**Real Windows + Cloudflare + phone scan acceptance is pending.** Do not call the 7-second latency fixed until the user runs the package and reports the real phone scan-to-destination time.
