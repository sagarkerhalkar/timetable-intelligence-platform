# 2026-08-14 - QR sub-600 ms edge redirect target

## User requirement
Target QR opening performance: QR scan/tap to redirect response should be approximately <= 0.6 second where network conditions allow.

## Scope boundary
This target applies to the NextToppers QR redirect overhead. Full rendering time of the final third-party destination cannot be guaranteed because it depends on the destination origin, DNS/TLS/network, device, and destination page weight.

## Locked fast-path architecture
For anonymous tracked QR codes, the critical path must be:

1. Browser requests `https://q.nexttoppers.workers.dev/q/<slug>`.
2. Cloudflare Worker reads the destination from edge routing storage (KV or another edge-native store).
3. Worker immediately returns HTTP 302 with `Location: <destination>`.
4. Analytics/logging is queued with `ctx.waitUntil()` and MUST NOT be awaited before returning the redirect.

## Prohibited in the <=0.6 s fast path
- No Next.js/HTML scan page.
- No client-side JavaScript before redirect.
- No `setTimeout()` redirect delay.
- No synchronous fetch to `nexttoppers.sagarkerhalkar.com` or local FastAPI/SQLite/Tunnel before redirect.
- No synchronous analytics write before redirect.
- No image/logo/branding screen before redirect.

## Analytics trade-off
Immediate edge redirect can still capture request-level analytics such as Cloudflare country/colo/network metadata, User-Agent derived browser/OS/device class, referrer/source, and a first-party visitor cookie/ID. Browser-JavaScript-only fields such as screen dimensions or browser timezone cannot be collected before an immediate redirect without reintroducing an intermediate page and latency.

## Safety requirement before any new deployment
Because the previous v1.0.29.x installer chain left multiple Worker/KV/API rollback attempts, do not deploy another update until a read-only state inspection confirms the currently live Worker version, Worker bindings, KV namespace/binding, API 3550 state, web 3500 state, protected 3457 state, and production DB integrity/path.

## Acceptance
- Worker response must identify edge route source.
- Benchmark redirect overhead separately from final destination load.
- Measure p50/p95 across multiple warm scans; one phone scan is not sufficient for a commercial performance claim.
- Do not claim a guaranteed <=0.6 s full destination load.

## Status
Requirement locked. No new production deployment in this entry.
