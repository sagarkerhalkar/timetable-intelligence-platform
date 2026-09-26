# v1.0.24 Validation

## Local/source validation completed

- Changed Python files compile.
- Fresh database template/bulk/provenance harness passed.
- Old-style database migration to `template_id` + template indexes passed.
- Template create/list/count passed.
- Bulk creation of multiple unique QR campaigns passed at database layer.
- Template deletion preserved generated QRs.
- Shared asset reference counting across templates + QRs passed.
- New/changed QR TypeScript/TSX files transpiled with zero syntax diagnostics.
- Installer payload audit found all declared update files present.
- Protected port 3457 checks remain present.

## Permanent regression coverage added

`test_v124_qr_templates_bulk.py` covers:
- multiple templates + duplicate/default behavior;
- bulk creation using one template;
- independent analytics for A/B/C;
- rejection of Direct templates for tracked Bulk analytics;
- template deletion preserving generated QR campaigns.

## Not yet claimed

Local validation does **not** prove the real Windows deployment. Before merge to stable `v1`, the Windows installer must complete:
- full backend test suite;
- web tests;
- strict TypeScript;
- full Next.js production build;
- all-tab runtime smoke checks;
- QR lifecycle checks;
- template/bulk/per-QR analytics acceptance;
- existing Test Monitor and Sheet Updates checks;
- no rollback.
