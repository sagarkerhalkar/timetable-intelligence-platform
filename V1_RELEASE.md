# v1 Windows LAN release

Current candidate package: `timetable-intelligence-platform-v1.0.15.1-stable-test-gate-fix.zip`

SHA-256: `28a13f66f9cf1d6732877663a26d3616a67bc09f0e41dac8667e3b98ba17792c`

## v1.0.15.1 stability / calendar-independent parser-test correction

- v1.0.15 correctly rolled back on 10 Aug 2026 when two official-parser tests became calendar-dependent.
- The Science and Humanities fixtures hard-coded Tuesday 4 Aug 2026. On Monday 10 Aug that date moved into the previous week, so the production parser correctly added a current-week recurring fallback and the old `len(items) == 1` assertions failed.
- The production parser business logic is unchanged.
- The subject/schedule tests now use the Tuesday of the active India week.
- A separate regression verifies previous-week planner data produces the intended current-week recurring fallback.
- The v1.0.15 Monday current-week fix remains: Monday 10 Aug 2026 maps to 10-16 Aug 2026.
- v1.0.14 performance work, v1.0.14.1 pagination repair, v1.0.13 one-click navigation and v1.0.12 human-readable Sheet Updates/Test logic are retained.
- The release package removes compiled Python cache files.
- The Windows installer still requires the full backend suite, web unit tests, strict TypeScript, full Next.js build, API version check and all-main-tab smoke checks before accepting the release. Any failure rolls back.

The working LAN deployment remains `http://156.156.40.51:3500` and protected port 3457 is not changed.

The release excludes databases, credentials, recipients, Google Sheet data, logs, runtime files and backups.
