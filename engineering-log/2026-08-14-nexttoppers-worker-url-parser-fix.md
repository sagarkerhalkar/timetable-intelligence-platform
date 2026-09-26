# 2026-08-14 — NextToppers Worker URL parser failure and corrective action

## User-visible failure

The v1.0.27 deployment flow reached Cloudflare Wrangler, but the wrapper failed with:

`Worker deployed but Wrangler output did not contain the assigned workers.dev URL.`

The user then confirmed the live Worker URL manually as:

`https://q.nexttoppers.workers.dev/`

## Root cause

The deployment wrapper incorrectly treated parsing Wrangler's human-readable console output as the source of truth for the deployment URL. Current Wrangler output can change and may emit help/global-flags text or omit a URL in the specific captured stream/layout. The Worker itself can still be successfully deployed.

This was an installer/parser failure, not an application/database failure.

## Safety state

- App public QR base was NOT changed by the failed v1.0.27 run.
- Production database was NOT migrated or rewritten.
- Existing QR rows/history were NOT deleted.
- Protected port 3457 was not touched.

## Corrective action

Do not redeploy or guess the Worker URL again. Use the user-confirmed live Worker URL directly:

`https://q.nexttoppers.workers.dev`

The corrective package v1.0.27.1 bypasses deployment-output parsing, verifies the supplied Worker URL from the Windows host, then invokes the existing guarded public-base updater with that exact URL. The updater keeps old printed QR routes compatible and changes only NEW tracked QR generation after tests/build pass.

## Corrective package

File: `NEXTTOPPERS_QR_EXACT_WORKER_URL_FIX_V1_0_27_1.zip`

SHA-256: `b713955a08fd8f7ef667128bdb5c5e5de981bc9d2e9b23ea44f817b2a278745d`

Local package validation:

- ZIP CRC: PASS
- exact public base embedded: `https://q.nexttoppers.workers.dev`
- Wrangler redeploy/parsing removed from this corrective package
- guarded DB/source/test/build updater retained

Real Windows acceptance is still pending.

## Acceptance

After v1.0.27.1 succeeds, create one completely new tracked QR. Its public/encoded URL must begin with:

`https://q.nexttoppers.workers.dev/`

The new QR must not encode `sagarkerhalkar.com`. Existing saved/printed QRs are intentionally not rewritten.

## Cloudflare note

Cloudflare documents Workers URLs as `<worker-name>.<account-subdomain>.workers.dev`. For this account, the confirmed values are worker `q` and account subdomain `nexttoppers`, yielding `q.nexttoppers.workers.dev`.
