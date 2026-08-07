# v1.0.14.1 pagination contract fix

## Failure from Windows validation

The v1.0.14 installer correctly ran the full backend suite and rolled back after one regression failed:

`tests/test_sync_and_routes.py::test_out_of_range_page`

Expected: HTTP 404 for `/api/v1/timetable?page=99&page_size=1` when timetable records exist but the requested page is beyond the last available page.

Actual in v1.0.14: HTTP 200 with an empty `items` list.

## Root cause

v1.0.14 moved timetable filtering/pagination into SQLite for speed. That correctly avoided loading/deserializing the full timetable table, but the route stopped using the older `_paginate()` helper and therefore missed its out-of-range rule.

## Fix

The route now calculates `pages = max(1, ceil(total/page_size))` from the SQL total and raises HTTP 404 when `total > 0` and `page > pages`.

An actually empty result set still treats page 1 as valid.

The fast SQL implementation remains unchanged; no full-table Python scan is reintroduced.

## Packaging

Corrected package: `timetable-intelligence-platform-v1.0.14.1-pagination-contract-fix.zip`

SHA-256: `9a11d8fb9fed005bd8a1c676b015a792514f8d54b2684cd4fde636fa33eecca0`
