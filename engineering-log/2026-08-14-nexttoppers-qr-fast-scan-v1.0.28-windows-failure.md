# 2026-08-14 — NextToppers QR Fast Scan v1.0.28 Windows acceptance failure

## Status

**v1.0.28 NOT ACCEPTED.** Production database was not migrated, deleted, or replaced. The installer restored previous API source/runtime after failure. The Worker fast-scan code did **not** become active.

## First acceptance failure

```text
NOT ACCEPTED: Updated q Worker health endpoint did not become live.
API source rollback attempted; production DB was not migrated/deleted.
```

The surrounding Wrangler output showed Wrangler's top-level help/options (for example `--profile`, `--version`, and the generic issue-reporting footer) instead of output from a real `deploy` or `rollback` command.

## Root cause

The v1.0.28 PowerShell helper was declared as:

```powershell
function Run-Wrangler([string[]]$Args)
```

PowerShell already uses `$args` as an automatic variable. In the real Windows run the intended Wrangler subcommand arguments were not forwarded. `npx wrangler@latest` therefore ran without the requested subcommand, printed its general help screen, and returned success. The installer incorrectly logged PASS even though Worker `q` had not been deployed.

The same argument-forwarding defect affected the rollback invocation. Because no real deploy had occurred, the previous Worker remained active anyway.

## Fix — v1.0.28.1

- Rename the helper argument variable to `$CommandArgs`.
- Log the exact Wrangler command before execution.
- Treat a bare Wrangler general-help screen as failure rather than PASS.
- Require real `wrangler whoami` execution.
- Require real `wrangler deploy --config wrangler.jsonc` execution.
- Verify `wrangler deployments status --name q --json` after deploy.
- Allow up to 120 seconds for the new Worker fast-path health marker.
- Attempt rollback only after a real Worker deploy has occurred.
- Keep the existing DB guard, isolated backend tests, API-only restart, port 3500 protection, and protected port 3457 protection.

## Package

Local cumulative Windows package:

`NEXTTOPPERS_QR_FAST_SCAN_V1_0_28_1.zip`

SHA-256:

`e0cff4d5e5fc93d40014d4e1fb4d529f7d10c0cf522c6da0248392c4d283eab8`

ZIP CRC: **PASS**

## Cloudflare command contract checked

Current Cloudflare Wrangler documentation confirms `wrangler rollback [<VERSION_ID>] [OPTIONS]`, supports `--name` and `--message`, and documents `wrangler deployments status` for production deployment state. v1.0.28.1 follows that command structure.

## Next action

Run v1.0.28.1 on the real Windows host. Acceptance requires the explicit success banner plus a real phone scan-to-destination timing. Do not call the 7-second performance issue solved until that phone test passes.
