# 2026-09-26 — QR V7.1 Windows ampersand/utm sync fix

## User-visible failure
Editing a tracked QR failed with:
- `Cloudflare QR sync failed; QR edit was rolled back`
- Wrangler: `Missing required option: exactly one of --binding and --namespace-id must be provided`
- Windows: `'utm_medium' is not recognized as an internal or external command`
- libuv assertion after the broken command invocation.

Affected example slug: `eh72sp8`.

## Root cause
V7 passed the complete QR route JSON as an inline Wrangler positional VALUE:

`wrangler kv key put <KEY> <JSON VALUE> --namespace-id <ID> --remote`

On Windows Wrangler may be executed through `npx.cmd`. A target URL containing `&utm_medium`, `&utm_source`, or another ampersand can be interpreted by `cmd.exe` as a command separator before Wrangler receives the remaining arguments. That truncates the command, which explains both the stray `utm_medium` command and Wrangler seeing no `--namespace-id`.

This is not a limit on the number of QR edits.

## Permanent fix V7.1
Use Wrangler's file transport instead of putting the route JSON on the Windows command line:

`wrangler kv key put <KEY> --path <TEMP_JSON_FILE> --namespace-id=<ID> --remote`

The temporary UTF-8 JSON file is deleted after the KV write. KV readback still verifies slug, target URL, and active state.

## Acceptance contract
V7.1 must not declare success from syntax alone. It creates one temporary tracked QR whose destination contains `&utm_medium`, then changes the SAME QR twice more using URLs with multiple `&` query parameters. Each target must become visible on the public QR. Active/Inactive is also exercised and the temporary QR is removed.

Expected success message:
`SUCCESS - PERMANENT QR AUTO-SYNC V7.1 IS WORKING`

## Scope
- Generic for all tracked QR codes, not one slug.
- Same QR / same slug remains reusable when destination changes.
- No manual helper CMD after each edit once V7.1 passes.
- Only API 3550 is restarted by installer.
- Web 3500, protected 3457, Sheets, Timetable, Test Monitor, Worker code, Worker deployment, and Worker secrets are not modified.

## Package
`NEXTTOPPERS_QR_PERMANENT_DYNAMIC_AUTO_SYNC_V7_1.zip`

SHA-256:
`8953ad44568f615e49555e12f692aee69069a0fa79e916d38ab1a81911eaffe9`

Local package checks before delivery:
- ZIP CRC: PASS
- Python syntax: PASS
- installer self-test: PASS
- inline Wrangler JSON VALUE removed: PASS
- Wrangler `--path` transport installed: PASS

Real Windows/Cloudflare acceptance is pending user execution; do not promote to stable `v1` until that acceptance passes.
