# Mandatory GitHub Handoff Policy

Status: **MANDATORY for every future development session on this project.**

GitHub is the engineering source of truth for `sagarkerhalkar/timetable-intelligence-platform`. A future chat/developer must be able to continue the project from GitHub without depending on an inaccessible prior chat.

## What must be written to GitHub before a development session ends

Every engineering-relevant part of the session must be recorded, including:

1. User requirements and requirement changes.
2. Scope explicitly preserved / not changed.
3. Architecture and product decisions.
4. Runtime assumptions, ports, paths and protected resources.
5. Exact files changed, added or removed.
6. Installer/package files and deterministic package-build instructions.
7. Commands and validation gates used.
8. Every meaningful FAIL result.
9. Root cause of each failure.
10. Exact fix applied for each failure.
11. Every PASS result after the fix.
12. TypeScript, backend, frontend, build and runtime-test status.
13. Windows installer result.
14. Rollback result if an installer fails.
15. Package filename and SHA-256 when a package is produced.
16. Git branch, PR and commit used for the release candidate.
17. Exact unresolved items / blockers.
18. Exact next action for the next chat/developer.
19. Any important lesson learned so the same mistake is not repeated.

## Chat-to-GitHub rule

All engineering chat for this project is part of the handoff record. Requirements, changes, errors, failures, successes, fixes, validation results, user corrections, process complaints that affect development, and unresolved decisions must be written to GitHub during the same development session.

A future chat must not need the previous ChatGPT conversation to know what was requested, what failed, what was fixed, what passed, what code/package exists, and what must happen next.

A concise technical record may replace repetitive conversational wording, but no engineering meaning may exist only in chat. When the user explicitly requires wording to be preserved, retain it in the chronological engineering log unless it contains sensitive/private information.

## Delivery-priority rule

GitHub handoff work must **not delay delivery of working code/package** for hours. When a usable release candidate or installer is ready, provide it to the user immediately and update GitHub in the same turn/session. Do not spend a long session only repairing documentation while withholding the code artifact.

For long development sessions, update GitHub incrementally after meaningful milestones/failures so the final handoff is small and does not become a separate multi-hour task.

## Required repository locations

- `docs/CURRENT_PROJECT_CONTEXT.md` — current authoritative product/runtime state.
- `docs/GITHUB_MANDATORY_HANDOFF_POLICY.md` — this permanent policy.
- `engineering-log/YYYY-MM-DD-<release-or-topic>.md` — chronological session evidence containing requirements, failures, fixes and PASS results.
- `release-source/<version>/` — reproducible sanitized source for the release.
- `reports/VALIDATION_<version>.md` — validation evidence for the release.

If a distributable package cannot be safely stored directly in the repository, GitHub must still contain all sanitized source and deterministic build instructions required to regenerate it, together with the package SHA-256.

## Mandatory end-of-session checklist

A development session is not considered handed off until GitHub contains:

- current requirements;
- actual changed source;
- engineering log;
- validation state;
- package/build state;
- failures and fixes;
- next action.

The developer/assistant must verify the pushed/committed files exist on the release-candidate branch before claiming the handoff is complete.

## Safety / public repository exclusions

The repository is public. The following must **never** be committed merely to satisfy the handoff rule:

- credentials, passwords, API keys, OAuth secrets;
- `.env` secrets;
- cookies, access tokens or refresh tokens;
- databases containing private/runtime/customer data;
- private Google Sheet contents;
- recipient/member/teacher personal data;
- customer uploads or private assets;
- private runtime logs containing sensitive data.

For excluded material, record only sanitized structure, hashes, test outcomes or reproduction instructions as appropriate.

## Stable-release rule

Stable branch `v1` must remain unchanged until the real Windows release candidate passes the complete acceptance gate without rollback. Release work stays on a separate release-candidate branch/PR until then.

## Runtime protections

Current runtime protections remain authoritative unless explicitly changed and recorded:

- Windows target: `D:\timetable-intelligence-platform`
- Web: `3500`
- API: `3550`
- Port `3457` is protected and must not be touched.

## Purpose of this policy

This rule exists specifically to prevent a repeat of the v1.0.25 handoff gap where documentation existed in GitHub but some exact Windows runtime page source was not committed, forcing a later session to collect source again from the installed machine, and to prevent GitHub bookkeeping from delaying delivery of the actual code package to the user.
