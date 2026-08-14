# 2026-08-14 — Old QR compatibility redirect: Free-plan field limitation and revised design

## User goal
Keep every already-created/printed QR image unchanged while moving the browser from the old public tracker host to the new Cloudflare Worker host after the QR is opened.

Old encoded public URL pattern:
`https://nexttoppers.sagarkerhalkar.com/q/<slug>`

New Worker public host:
`https://q.nexttoppers.workers.dev`

## Real Cloudflare dashboard failure
The proposed Single Redirect expression used `cf.worker.upstream_zone` to exclude Worker-origin subrequests and prevent a redirect loop. The user's actual zone dashboard rejected the expression with:

`the use of field cf.worker.upstream_zone is not allowed`

This is a real account/rules-engine capability limitation for this Single Redirect context. Do not keep retrying that field and do not weaken the safety requirement by creating a loop-prone all-/q/ redirect while the Worker still proxies to the old hostname.

## Revised safe design
Use a dedicated hidden origin hostname on the existing Cloudflare Tunnel, for example:
`https://ntqr-origin.sagarkerhalkar.com`

Map that hostname to the same current web service, normally:
`http://127.0.0.1:3500`

Then set the Worker's `ORIGIN_BASE` variable to the hidden origin hostname instead of `https://nexttoppers.sagarkerhalkar.com`.

After the Worker no longer fetches the old public QR hostname, the old QR Single Redirect can be simplified to supported fields only:

Match:
`http.host eq "nexttoppers.sagarkerhalkar.com" and starts_with(http.request.uri.path, "/q/")`

Dynamic target:
`concat("https://q.nexttoppers.workers.dev", http.request.uri.path)`

Status: `302`
Preserve query string: `ON`

This avoids an old-host -> Worker -> old-host redirect loop because Worker backend fetches go to the dedicated origin hostname.

## Safety
- Do not modify or regenerate old QR images.
- Do not rewrite historical QR database rows for this compatibility change.
- Keep old QR slugs/destinations/analytics intact.
- Redirect only `/q/` on the old public hostname; do not redirect the timetable application globally.
- Keep protected dev port 3457 untouched.
- Use 302 until real-device acceptance succeeds; do not switch to 301 during testing.

## Acceptance pending
1. Add the dedicated tunnel hostname to the existing tunnel and verify it reaches the current service.
2. Change Worker `ORIGIN_BASE` to that hostname and deploy/save.
3. Verify a known Worker QR still reaches its real destination and analytics.
4. Create the simplified Single Redirect with host + `/q/` only and Preserve query string ON.
5. Scan an existing printed QR without regenerating it.
6. Confirm browser moves from old host to `q.nexttoppers.workers.dev` and final destination/analytics still work.
