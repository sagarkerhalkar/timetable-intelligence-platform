# v1.0.15 stability and current-week boundary correction

## Failure reproduced from 10 August 2026 recording

On Monday 10 August 2026, **This week** displayed 3-9 August even though Today/Next Available correctly used 10 August.

## Root cause

`indiaWeekDates()` parsed the India civil date as `YYYY-MM-DDT00:00:00+05:30` and then used `getUTCDay()`.
Monday 00:00 in India is Sunday 18:30 UTC, so every Monday was incorrectly treated as Sunday and moved six days backward to the previous Monday.
This was a latent boundary bug that the previous web test suite did not cover.

## Correction

- Treat `YYYY-MM-DD` as a civil date and perform week arithmetic from UTC midnight of those calendar numbers.
- Monday stays in its own week.
- Sunday maps to the Monday six days earlier.
- Month/year boundaries are deterministic and independent of the Windows/server timezone.
- Invalid civil dates are rejected.

## Stability gates added

The Windows installer now runs all of these before accepting the build:

1. Complete Python backend tests.
2. Web unit tests (`npm test`) including deterministic Monday, Sunday and year-boundary week tests.
3. Strict TypeScript validation.
4. Complete Next.js production build.
5. API version/health check.
6. HTTP smoke checks for every main navigation tab: Today, This Week, Tomorrow, Next Schedule, Learning Files, Google Sheets, Sheet Updates, Test Monitor, Notifications and App Status.
7. Existing Test Monitor cache/latency and Sheet Updates API checks.

Any failure restores the previous files, databases and `.next` build.

Package SHA-256: `932ef28a3d904af378bc0a1163084f99c1beca3bde17469faaa360ec93919c6d`
