# v1.0.15.1 stable test-gate correction

## Windows failure reproduced

v1.0.15 correctly rolled back because two official-parser tests failed on 10 Aug 2026:

- `test_science_falls_back_to_bounded_timetable_schedule`
- `test_humanities_uses_schedule_without_misclassifying_political_science`

Both tests hard-coded Tuesday 4 Aug 2026 and asserted exactly one parsed item. On 10 Aug that date had moved into the previous week. The production parser intentionally bridges a recent Weekly Planner gap using the recurring Time Table schedule, so it added the current-week Tuesday fallback and the old fixtures saw two legitimate dates.

## Correction

- Keep the production parser logic unchanged.
- Make the Science and Humanities subject/schedule fixtures use the Tuesday of the active India week.
- Add a separate regression proving previous-week planner data generates the intended current-week recurring fallback.
- Preserve the v1.0.15 Monday/current-week boundary correction and all prior performance/navigation/human-readable fixes.
- Remove compiled Python cache artifacts from the release package.

## Validation

The reconstructed official-parser regression file passes all 12 parser tests. The Windows installer remains the authoritative release gate and must pass the complete backend suite, web unit tests, strict TypeScript, full Next.js build, API version check and all-main-tab smoke checks before accepting v1.0.15.1.

Package SHA-256: `28a13f66f9cf1d6732877663a26d3616a67bc09f0e41dac8667e3b98ba17792c`
