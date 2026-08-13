# v1.0.25.1 Validation Report

## Windows failure observed on 2026-08-13

The user ran v1.0.25 on the real Windows server. Windows PowerShell failed before executing the installer.

Primary error:

`INSTALL_V1_0_25.ps1:243 char:98 - Unexpected token 'shared' in expression or statement.`

Cascade parser errors then reported missing arguments around the `paginateItems(...)` source-contract strings and illegal `&` characters inside URLs on lines 302-303.

Result: **FAIL**. v1.0.25 was not accepted.

Because this was a parse-time failure, the PowerShell file never executed; no v1.0.25 payload apply step ran from this attempt.

## Root cause

The installer contained one non-ASCII em dash in the marker string:

`v1.0.25 - shared pagination + larger QR library`

The original file had the typographic em dash encoded as UTF-8 without a BOM. Windows PowerShell 5.1 can decode such a script using the legacy Windows code page. The UTF-8 bytes became mojibake (`a-circumflex / euro / smart-quote` style text). The resulting smart quote was interpreted as a PowerShell quote delimiter, terminating the marker string early. All later comma and ampersand diagnostics were cascade parser errors rather than independent product-code failures.

## v1.0.25.1 correction

- `INSTALL_V1_0_25_1.ps1` is ASCII-only.
- `PRECHECK_V1_0_25_1.ps1` runs Windows PowerShell's own `System.Management.Automation.Language.Parser` against the complete installer before any backup/apply/stop/build/restart action.
- The precheck also rejects non-ASCII characters in the installer.
- The installer verifies every payload file size and SHA-256 against `PAYLOAD_MANIFEST.json` before apply.
- Existing v1.0.25 QR/timetable product scope is unchanged.
- Port 3457 remains protected.

## Source/package validation completed before publishing v1.0.25.1

- Installer ASCII-only audit: PASS.
- Precheck ASCII-only audit: PASS.
- Payload manifest: 8/8 files size + SHA-256 PASS.
- ZIP CRC/integrity test: PASS.
- Deterministic package build: PASS; two builds were byte-for-byte identical.
- Package SHA-256: `83192ab526117e3b91cea39978ac8f57749e2dfee63421997a0563a59b35f8ef`.

## Windows acceptance status

**NOT YET ACCEPTED.** The corrected package still must run on the real Windows installation. The first line of meaningful output must include:

`PASS: Windows PowerShell parser precheck completed with zero errors.`

After that, the existing full backend/web/typecheck/build/runtime/rollback acceptance gate remains blocking.
