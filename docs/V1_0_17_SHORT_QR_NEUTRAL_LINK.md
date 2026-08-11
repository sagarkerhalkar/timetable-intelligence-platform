# v1.0.17 — Short QR + neutral-link mode

## User-facing QR flow

The stable tracker is now compact:

`https://<public-base>/q/<7-character-code>`

For `nexttoppers.sagarkerhalkar.com`, this means QR campaigns no longer need the long `/backend/api/v1/qr/scan/...` path.

## Optional hide-personal-domain mode

When enabled during QR creation, the app requests a neutral `is.gd` short URL that points to the stable `/q/<slug>` tracker. The QR image encodes the neutral link, the local app still records scan analytics, and the visitor is immediately redirected to the Google Form.

This mode is optional because the external shortener has its own availability, rate-limit and safety policies. The stable own short URL remains available when third-party shortening is not desired.

## Installer correction

`qrcode[pil]` is now a normal backend dependency in `services/api/pyproject.toml`. The installer uses dependency-aware `pip install -e .` instead of `--no-deps`, so QR image support is installed before the backend suite runs. The fragile pre-install import probe is removed.

## Analytics/privacy

- total human scans;
- approximate anonymous unique visitors;
- country/device/browser analytics;
- recent scan history and CSV export;
- bot/preview hits excluded from person totals;
- no raw IP storage;
- no Google Form responses copied.

The cumulative Monday/current-week, parser stability, performance, Test Monitor, Sheet Updates and pagination fixes remain included.
