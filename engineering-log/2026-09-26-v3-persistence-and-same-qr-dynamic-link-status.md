# 2026-09-26 — V3 persistence and same-QR dynamic link status

## User question
User asked whether the QR fix will start automatically after restart and whether the requirement “same QR, destination link can change” is fully completed.

## Current V3 behavior
- Permanent QR slug remains `smfffdy`.
- Cloudflare KV route survives machine/API reboot; V3 does not need to be rerun just because Windows restarts.
- `qr_fast.py` patch is persisted on disk and will be loaded whenever API 3550 starts.
- V3 does **not** install a new Windows startup task/service. Existing application startup behavior is left unchanged.
- Therefore, if API 3550 was already configured to auto-start before this fix, that existing mechanism remains responsible for starting it after reboot.

## Same QR / changeable destination
- The same printed QR and slug are preserved.
- Changing the local QR destination does not require QR regeneration/reprint.
- In V3 urgent mode, Cloudflare edge/KV does **not** auto-sync after a destination edit.
- After changing the destination in the existing QR Edit UI, run `SYNC_QR_SMFFFDY_AFTER_LINK_CHANGE.cmd` to push the current `smfffdy` route to the existing KV namespace.
- Manual sync is required only after link/active changes, not after every reboot.

## Remaining work for full automation
A later QR-only change should make local QR edit/active endpoints automatically push the existing slug to Cloudflare edge using a stable non-interactive credential path. This must not deploy an uncertain Worker version, regenerate the QR, change the slug, touch port 3457, or disturb Timetable/Sheets/Test Monitor.
