# NextToppers QR public URL fix

Date: 2026-08-13

Observed failure: newly generated tracked QR codes still use the previous public hostname.

Cause: the QR backend historically used a fixed public tracker hostname. UI branding changes do not change the URL encoded into a QR image.

Required behavior: new tracked QR records, generated images, preview, Copy QR Link and Open QR must use the configured NextToppers QR public base. Existing QR IDs, slugs, destination URLs and analytics history remain unchanged. Existing printed QR codes remain backward compatible. No database replacement or deletion is permitted. Port 3457 remains protected.

Acceptance is pending a real Windows run.