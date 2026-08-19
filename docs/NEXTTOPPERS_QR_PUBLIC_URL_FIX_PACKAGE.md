# QR public URL corrective package

Date: 2026-08-13

Artifact: `NEXTTOPPERS_QR_WORKER_PUBLIC_BASE_FIX.zip`

SHA-256: `306d46d11e9c2df11af3177bef12864aec5e2a3bb7ddc75fb36307dd7e2acc9c`

Purpose: change the public base used by newly generated tracked QR codes instead of only changing visible branding. Existing database rows are not migrated or deleted. Existing printed QR codes remain backward compatible. Installer acceptance requires backend tests, web tests, TypeScript validation, optimized web build, runtime health checks, and protected port 3457.

Real Windows acceptance: PENDING.