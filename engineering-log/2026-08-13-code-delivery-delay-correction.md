# 2026-08-13 — Code Delivery Delay / Process Correction

## User correction

The user explicitly complained that the session had taken almost three hours while the usable code package still had not been given, despite the repeated requirement that all development chat, errors and successes be recorded in GitHub.

User requirement reinforced:

- GitHub logging is mandatory for all engineering chat, requirements, failures, fixes and successes.
- GitHub bookkeeping must not block or delay the actual code/package delivery.
- When code is ready, provide the package immediately and record the same state in GitHub during the same session.

## Process failure

FAIL — too much session time was spent repairing GitHub handoff/reconstruction details before presenting the already-generated Windows package to the user.

## Root cause

The handoff-repair task was incorrectly allowed to take priority over artifact delivery. Additional package-storage experiments (including Base64 reconstruction work) also added unnecessary delay after a deterministic local package and release-source snapshot already existed.

## Fix

1. Make the delivery-priority rule permanent in `docs/GITHUB_MANDATORY_HANDOFF_POLICY.md`.
2. Present the working v1.0.25 package and release-source snapshot immediately.
3. Keep actual release source, deterministic builder and installer source in `release-source/v1.0.25/`.
4. For future long sessions, update GitHub incrementally after meaningful milestones instead of creating a large handoff-only phase at the end.
5. Keep stable `v1` unchanged until real Windows acceptance passes without rollback.

## Current artifact state

Usable Windows release-candidate package:

`timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip`

Canonical SHA-256:

`56a02100fd2d85969384ad855bd91afa0e25684a296ab0e9482fe597196b09f0`

Release-source snapshot is also available and contains the v1.0.25 runtime source, deterministic package builder, installer source, validation report, mandatory GitHub policy, engineering evidence and sanitized recovered runtime snapshot.

## Acceptance status

The package is a release candidate. Real Windows acceptance is still required. The installer itself runs backend tests, functional web regression tests, real TypeScript typecheck, Next.js production build, existing runtime API checks, QR page smoke tests and temporary QR lifecycle/independent-analytics checks; it rolls back on blocking failure.

Port 3457 remains protected and must not be touched.
