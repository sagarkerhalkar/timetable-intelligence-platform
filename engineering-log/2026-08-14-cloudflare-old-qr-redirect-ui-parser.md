# 2026-08-14 - Cloudflare old QR redirect rule UI parser issue

## User-visible failure
On Cloudflare Single Redirect creation for old QR compatibility, the dashboard rejected the custom expression and showed both:
- `A list with this name already exists for this account`
- parser failure because the dashboard had appended an empty wildcard expression `(http.request.full_uri wildcard r"")` after the intended custom filter.

The screenshot also showed `Preserve query string` was OFF.

## Intended behavior
Keep old printed QR images unchanged. Direct visitor requests to `https://nexttoppers.sagarkerhalkar.com/q/...` should redirect to `https://q.nexttoppers.workers.dev/q/...`, while Worker-origin subrequests must bypass the redirect to avoid a loop.

## Corrective UI guidance
Cancel the broken draft and create a fresh Single Redirect with a unique rule name. Use a clean custom expression with `cf.worker.upstream_zone eq ""` to match only direct visitor requests:

`http.host eq "nexttoppers.sagarkerhalkar.com" and starts_with(http.request.uri.path, "/q/") and cf.worker.upstream_zone eq ""`

Dynamic target:

`concat("https://q.nexttoppers.workers.dev", http.request.uri.path)`

Use HTTP 302 for first acceptance and enable Preserve query string.

## Safety
No application source, database, QR image, QR ID, destination, analytics history, API runtime, or protected port 3457 is changed by this dashboard-only correction.

## Acceptance pending
Scan one old printed QR and verify it redirects to the Worker URL, then reaches the original destination without a loop and analytics still record normally.
