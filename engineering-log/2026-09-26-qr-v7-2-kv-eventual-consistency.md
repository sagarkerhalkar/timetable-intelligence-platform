# QR V7.2 - eventual consistency fix for repeated tracked-QR edits

Date: 2026-09-26
Branch: nexttoppersqr

## Production evidence

V7.1 Windows acceptance:
- API 3550 restarted successfully.
- New tracked QR with `&utm_medium` synchronized successfully.
- Same QR edit #2 with ampersand query parameters synchronized successfully.
- Edit #3 failed with `KV target readback mismatch`.
- Installer rolled back to the previous V7 runtime.

The older V7 error on real QR edits therefore reappeared after rollback:
- `'utm_medium' is not recognized as an internal or external command`
- Wrangler `Missing required option: exactly one of --binding and --namespace-id must be provided`

## Root cause

V7.1 proved the `--path` transport solves Windows command-line splitting of URLs containing `&`.

The edit #3 failure was a separate issue: the helper treated the first KV read immediately after a successful write as authoritative. Cloudflare Workers KV is eventually consistent and can briefly return the previous cached value after a write. A stale readback was therefore misclassified as a failed write, causing a valid local edit to roll back.

## V7.2 fix

Package: `NEXTTOPPERS_QR_PERMANENT_DYNAMIC_AUTO_SYNC_V7_2.zip`
SHA-256: `5c948e1d425ae608aa9a7c38bd62527cdb952aa3428bd0adf876ed7368c81a8a`

V7.2:
- keeps the Windows-safe Wrangler `--path` KV value transport;
- uses `--namespace-id=<id>`;
- retries KV readback for up to 75 seconds after a successful write;
- no longer rolls back a valid QR edit because the first read-after-write is stale;
- preserves the generic V7 automatic sync hooks for new tracked QR creation, repeated edits, Active/Inactive, Delete, and Bulk Create;
- restarts only API 3550;
- does not touch web 3500, protected 3457, Sheets, Timetable, Test Monitor, Worker code/deployment, or Worker secrets.

## Acceptance gate

Do not claim Windows production PASS until the server run ends with:

`SUCCESS - PERMANENT QR AUTO-SYNC V7.2 IS WORKING`

The acceptance flow still creates a temporary tracked QR, changes the same QR multiple times with `&utm_*` parameters, verifies public targets, checks Active/Inactive, and removes the temporary QR.

## Separate redirect UX issue

The current Worker source returns an HTML `scanHtml(...)` page for tracked QR codes and only returns HTTP 302 for `tracking_mode === "direct"`. This explains reports that tracked scans first open a web page. That behavior is separate from the auto-sync bug. Changing tracked anonymous URL QR codes to immediate HTTP 302 while preserving asynchronous analytics requires a Worker code change and should be handled as a separate, verified deployment after V7.2 auto-sync acceptance.
