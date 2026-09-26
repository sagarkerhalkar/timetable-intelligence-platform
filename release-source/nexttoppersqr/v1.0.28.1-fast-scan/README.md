# NextToppers QR Fast Scan v1.0.28.1

This is the cumulative Windows correction for the rejected v1.0.28 fast-scan installer.

## Real Windows failure fixed

v1.0.28 used a PowerShell Wrangler helper parameter named `$Args`. That collided with PowerShell's automatic `$args` variable, so the intended Wrangler subcommands were not forwarded. Wrangler printed its general help screen and exited successfully; the installer falsely treated that as a real deployment. Consequently the new `q` Worker health endpoint never became live.

v1.0.28.1 renames the parameter to `$CommandArgs`, logs each exact Wrangler command, rejects a generic-help response, verifies `whoami`, deploys Worker `q`, checks `deployments status`, and then verifies the fast-path health marker.

## Safety

- No production DB migration/delete/replace.
- DB integrity/count guard retained.
- Backend tests run against isolated temporary DB before runtime switch.
- Only API 3550 is restarted after validation.
- Web 3500 remains running.
- Protected dev port 3457 is untouched.
- Worker rollback is attempted only after a real deploy occurred.

## Cumulative local package

`NEXTTOPPERS_QR_FAST_SCAN_V1_0_28_1.zip`

SHA-256: `e0cff4d5e5fc93d40014d4e1fb4d529f7d10c0cf522c6da0248392c4d283eab8`

ZIP CRC: PASS.

The distributable ZIP is intentionally not mirrored here; use this repository for sanitized source/evidence and the locally generated checked package for Windows acceptance.

## Acceptance

Do not call the original approximately 7-second scan delay solved until the real Windows installer shows the explicit v1.0.28.1 SUCCESS banner and a phone scan confirms improved scan-to-destination time.
