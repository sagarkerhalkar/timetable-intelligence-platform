# v1.0.13 application patch map

This public patch map records the exact runtime areas changed without committing databases, credentials, recipients, Google Sheet data, logs or backups.

## `apps/web/app/page.tsx`

The four Today stream summary blocks are changed from plain `<span>` display elements to `next/link` links. Each link targets:

```tsx
/timetable?date=<today>&stream=<Commerce|Science|Humanities|Nirmaan>
```

The full card is keyboard accessible and includes an explicit “Open →” affordance.

## `apps/web/app/globals.css`

Adds clickable/hover/focus styling for `.today-stream-link` and immediate pending feedback for Test Monitor tabs.

## `services/api/app/database.py`

Adds `test_sheet_counts(source_id)` using one SQL aggregation:

```sql
SELECT sheet_name, COUNT(*) AS total
FROM test_records
WHERE source_id=?
GROUP BY sheet_name
ORDER BY total DESC, sheet_name COLLATE NOCASE
```

The existing indexed `list_test_records(source_id, sheet_names=[...])` path is used for selected tabs.

## `services/api/app/api/routes.py`

Adds:

```text
GET /api/v1/test-monitor/tabs
```

The main Test Monitor route now calls `Database.list_test_records(..., sheet_names=[sheet_name])` when a tab is selected instead of loading all test rows and filtering in Python.

## `apps/web/lib/api.ts`

Adds `getTestTabCounts()` for the lightweight Test tab endpoint.

## `apps/web/app/tests/page.tsx`

The previous selected-tab render performed an all-data `getTestMonitor()` call and then a second selected-tab `getTestMonitor(...)` call. v1.0.13 performs one selected monitor request in parallel with lightweight tab counts and source metadata.

## `apps/web/components/test-tab-switcher.tsx`

- clicked tab becomes active immediately;
- one pending click is visibly acknowledged;
- duplicate clicks on the already-pending tab are ignored;
- navigation uses `router.replace(..., { scroll: false })` so the page does not jump unnecessarily.

## `services/api/tests/test_v113_fast_navigation.py`

Adds regression coverage for SQL tab aggregation, direct selected-tab filtering and the lightweight tab endpoint.

## Cumulative preservation

The v1.0.13 Windows ZIP also carries forward the v1.0.12 Sheet Updates/Test Monitor human-readable changes, the Monday-Saturday-to-Sunday test rule, clickable changed links and the v1.0.11.1 strict TypeScript `cellParts()` repair.
