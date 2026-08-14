# 2026-08-14 - Worker hostname preflight failure and v1.0.27 corrective fix

## Windows failure evidence

Command package: `NEXTTOPPERS_QR_WORKER_PUBLIC_BASE_FIX.zip`

Observed at 2026-08-14 11:22 IST:

```text
[INFO] Target public QR base: https://q.nexttoppersqr.workers.dev
[INFO] Checking Worker URL before changing application source.
[FAIL] Worker URL is not reachable: https://q.nexttoppersqr.workers.dev . Fix/deploy the Worker first or run with -PublicQrBase YOUR_REAL_WORKER_URL.

NOT ACCEPTED
Source rollback attempted. Production DB was never rewritten.
```

## Cause

The previous corrective package guessed a workers.dev hostname before a Worker had actually been deployed. Cloudflare assigns the usable workers.dev route only after deployment, using the Worker name plus the authenticated account's configured workers.dev subdomain. Therefore `q.nexttoppersqr.workers.dev` was not a valid accepted production target.

The failed preflight was safe: it happened before source changes, database changes, or service restart.

## v1.0.27 corrective solution

Package: `NEXTTOPPERS_QR_WORKER_DEPLOY_AND_FIX_V1_0_27.zip`

SHA-256: `4763ceceedcaa98dbdc5b7be6cf551408f8b8d02a7fce3c0c7e56d6f7dd40eef`

ZIP CRC: PASS.

The new cumulative flow:

1. Use current Cloudflare Wrangler.
2. Check authentication; if needed open `wrangler login` so the account owner authenticates and grants access.
3. Deploy Worker `nexttoppers-qr` with `workers_dev=true`.
4. Parse the actual `https://<worker>.<account-subdomain>.workers.dev` URL printed by Wrangler.
5. Verify `/__nexttoppers_health` on that exact deployed URL.
6. Check Worker-to-origin reachability.
7. Only then invoke the existing safe application public-base patcher with the live Worker URL.
8. Keep old printed QRs and existing QR records intact.
9. No production DB migration/delete/replace.
10. Keep port 3457 untouched.
11. Run backend tests, web tests when present, TypeScript and Next.js production build before runtime switch.

## Worker behavior

- New QR public links use the deployed workers.dev hostname.
- Existing `nexttoppers.sagarkerhalkar.com` remains the backend origin behind the gateway for compatibility with the current tracking/analytics route and old printed QRs.
- Internal old-origin redirects/text links are rewritten to the Worker public origin where applicable.
- External final destination redirects are left intact.
- Gateway scan paths are `no-store` to avoid stale tracking responses.

## Acceptance still pending

Real Windows acceptance is pending. Required PASS:

- Cloudflare authentication available;
- Worker deployment succeeds;
- actual workers.dev URL detected;
- Worker health PASS;
- application patch/tests/build PASS;
- app restarts successfully;
- one completely new tracked QR encodes the new workers.dev hostname;
- scan reaches final destination;
- QR analytics still records the scan.

Do not claim the previous guessed hostname as valid. Do not use the old failed package for further acceptance.
