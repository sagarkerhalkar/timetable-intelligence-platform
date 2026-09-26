# QR V7.1 Windows ampersand / KV consistency hotfix

Date: 2026-09-26
Branch: nexttoppersqr

## Reported production failure

The V7.1 acceptance run passed:
- API 3550 restart
- NEW tracked QR edge sync with `&utm_medium`
- same QR edit #2 with ampersand query parameters

It then failed on edit #3 with:

`Cloudflare edge sync failed ... KV target readback mismatch`

The previous user-facing QR `eh72sp8` also continued to show the older V7 Windows command-line failure:
- `'utm_medium' is not recognized as an internal or external command`
- `Missing required option: exactly one of --binding and --namespace-id must be provided`

## Root causes

1. V7 used inline JSON as the positional Wrangler KV value. On Windows, Wrangler can be reached through `npx.cmd`; target URLs containing `&` may be split by `cmd.exe`, causing Wrangler to lose the later `--namespace-id` option.
2. The first V7.1 transport fix proved `--path` solves the ampersand problem, but its acceptance/readback still treated an immediate KV readback mismatch as a hard failure. Workers KV is eventually consistent, so a read immediately after a write can return the prior value.
3. Because acceptance failed, the installer correctly restored the previous V7 runtime; therefore the user's normal QR edit path still had the old inline-JSON command bug after rollback.

## Corrective package

Package: `NEXTTOPPERS_QR_PERMANENT_DYNAMIC_AUTO_SYNC_V7_1.zip`
SHA-256: `8953ad44568f615e49555e12f692aee69069a0fa79e916d38ab1a81911eaffe9`

The revised V7.1 package:
- uses a temporary UTF-8 file plus Wrangler `kv key put --path <file>` so URL query parameters never pass through the Windows command line;
- passes namespace as `--namespace-id=<id>`;
- removes the temp file immediately after the write;
- keeps the generic automatic sync hooks already installed by V7 for Create/Edit/Active/Delete/Bulk tracked QR operations;
- restarts only API 3550;
- does not touch web 3500, protected 3457, Google Sheets, timetable logic, Test Monitor, Worker source/deployment, or Worker secrets.

## Acceptance gate

The revised installer creates a temporary tracked QR with an ampersand query string, changes the SAME QR twice more with multiple `&utm_*` parameters, verifies public targets, checks Active/Inactive, and removes the temporary QR.

Windows production PASS must not be claimed until the user's server run finishes with:

`SUCCESS - PERMANENT QR AUTO-SYNC V7.1 IS WORKING`

## Important design rule

Tracked QR: permanent `/q/<slug>` pixels; destination can change without reprinting.
Direct QR: destination is encoded into pixels; changing destination requires a new QR.
