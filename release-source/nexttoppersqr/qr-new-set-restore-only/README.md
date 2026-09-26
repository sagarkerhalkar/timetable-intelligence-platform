# NextToppers QR New-Set Restore Only

Package delivered 2026-08-17:

- `NEXTTOPPERS_QR_NEW_SET_RESTORE_ONLY.zip`
- SHA-256 `d02b9f29ea345c44592cdcadf8bf2c03d49c65ba2a06d63e66dfcec26c32fd0d`

## Confirmed input state

The current API on port 3550 returns the older root QR dataset (`Count=24`, Aug-12 slugs such as `s66s4bb`, `rkph34u`, `mw9jmyn`). The newer service DB remains healthy with 23 QR records created Aug-14, including `vg3785v`, `mb365th`, `f336c43`.

## Apply scope

The package copies only these tables from `services/api/data/timetable.db` to `data/timetable.db`:

- `qr_templates`
- `qr_codes`
- `qr_scans`

It does not switch the global API database and does not modify core timetable/test/sheet tables, app source, running processes, Worker, KV, or port 3457.

## Safety contract

- verify integrity + foreign keys on both DBs
- prove API currently matches root QR slugs
- require source QR set to be newer
- SQLite backup of both DBs before write
- `BEGIN IMMEDIATE` for QR replacement
- core count guard inside the same transaction
- non-QR schema fingerprint guard
- post-write QR fingerprint equality
- post-write API exact slug-set verification
- QR-only rollback from backup on failed acceptance

## Windows command

Extract the ZIP and run:

`RUN_RESTORE_NEW_QR_ONLY.cmd`

On PASS, refresh the QR page with `Ctrl+F5`.

## Validation before delivery

- ZIP CRC PASS
- Python syntax PASS
- synthetic QR-only transaction PASS
- core-table preservation PASS
- no process-restart code PASS

The old root QR dataset is retained in the timestamped safety backup. The separate <=0.6-second Worker redirect optimization is intentionally not bundled into this data-recovery operation.
