# v1.0.25 Exact Windows Package

This folder preserves the **exact Windows acceptance ZIP** for v1.0.25 in GitHub so a future chat/developer does not depend on a prior ChatGPT attachment.

## Package

`timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip`

Expected SHA-256:

`56a02100fd2d85969384ad855bd91afa0e25684a296ab0e9482fe597196b09f0`

The binary ZIP is stored as five Base64 text parts because the GitHub connector used for this session writes UTF-8 text files:

1. `timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part00`
2. `timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part01`
3. `timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part02`
4. `timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part03`
5. `timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part04`

## Reconstruct on Windows PowerShell

Run from this folder:

```powershell
$base = 'timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip.b64.part'
$b64 = (0..4 | ForEach-Object {
    Get-Content -Raw ($base + ('{0:D2}' -f $_))
}) -join ''

$out = 'timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip'
[System.IO.File]::WriteAllBytes($out, [System.Convert]::FromBase64String($b64))
Get-FileHash $out -Algorithm SHA256
```

The reported hash **must** equal the expected SHA-256 above before the package is used.

## Acceptance status

This is still a **release candidate**. It must not be merged into stable `v1` until the package runs on the real Windows installation and completes all backend, web, strict TypeScript, Next.js build, runtime, QR lifecycle, Test Monitor, Sheet Updates and rollback gates without failure.

## Engineering continuity

Read before continuing development:

- `docs/GITHUB_MANDATORY_HANDOFF_POLICY.md`
- `engineering-log/2026-08-13-v1.0.25-handoff-and-runtime-recovery.md`
- `docs/CURRENT_PROJECT_CONTEXT.md`
- `reports/VALIDATION_V1_0_25.md`

Public-repository exclusions still apply: never commit credentials, tokens, databases, private Google Sheet contents, recipient/member data or private customer assets.