# v1.0.15.2 release-gate correction

## Authoritative Windows result from v1.0.15.1

- Backend suite: 75 passed.
- Web regression tests: 8 passed.
- Rollback occurred only because the existing `npm test` command also enforced whole-project V8 coverage thresholds.
- Reported coverage was 42.85% statements, 42.68% lines, 25.92% functions and 31.57% branches because large existing frontend modules are not yet unit-tested.

## Correction

The installer now runs the locally installed Vitest executable directly with coverage disabled for the functional release gate:

```text
node_modules\.bin\vitest.cmd run --coverage.enabled=false
```

This does not remove the project coverage goal. It separates a code-coverage quality metric from functional installation acceptance while the frontend suite is still small.

The following remain blocking:

1. full backend suite;
2. all web regression tests;
3. strict TypeScript;
4. full Next.js production build;
5. API version verification;
6. smoke checks for Today, This Week, Tomorrow, Next Schedule, Commerce, Science, Humanities, Nirmaan, Learning Files, Google Sheets, Sheet Updates, Test Monitor, Notifications and App Status;
7. cached Test Monitor tab checks and Sheet Updates API checks.

The Monday/current-week fix from v1.0.15 and the week-stable parser tests from v1.0.15.1 are unchanged.

Package SHA-256: `375333f6d554024d42370581a2d4b695c698945c8b76757b6d585d8846b8255c`
