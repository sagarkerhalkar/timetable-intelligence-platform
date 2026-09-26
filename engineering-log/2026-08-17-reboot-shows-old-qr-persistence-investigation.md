# 2026-08-17 - Reboot shows old QR UI / persistence investigation

## User report
After restarting the Windows machine, the application is showing the old QR experience and the user asks where the newer QR version went.

## Current evidence
- The recent QR performance packages did not reach a final accepted deployment. Each failed run attempted to restore the previous API source/runtime; some runs also rolled the Cloudflare Worker back.
- The production SQLite database was intentionally not migrated/deleted during those failures.
- Therefore a machine reboot can legitimately start the last persisted/autostarted accepted application build rather than a temporary failed candidate build.
- Cloudflare KV resources can survive Worker rollback, so local API/web code, Worker version and KV state may be mixed after several failed attempts.
- A prior confirmed project issue involved relative SQLite URLs selecting different DB files depending on process working directory. If newly-created QR records are actually missing rather than only the UI reverting, the rebooted API process must be checked for its exact command line, working directory and authoritative DB path before any write/fix is attempted.

## Safety decision
Do not apply another QR deployment patch until current post-reboot state is captured read-only.

Required read-only checks:
1. PID/executable/command line listening on ports 3457, 3500 and 3550.
2. Local API/web health and QR-fast route presence.
3. Authoritative `services/api/data/timetable.db` integrity, schema fingerprint and counts.
4. Current public `q.nexttoppers.workers.dev` health/build markers.
5. Current Wrangler deployment status and KV namespace list.
6. SHA-256/source markers for current local API QR source.

No restart, DB write, Worker deployment/rollback or KV modification should occur during this investigation.
