# 2026-08-17 - QR API response-shape check

## Context
The running app is healthy on web port 3500 and API port 3550. A read-only DB inspection confirmed the current service DB at `D:\timetable-intelligence-platform\services\api\data\timetable.db` is healthy and contains 23 newer QR records created on 2026-08-14, while the root DB contains 24 older QR records created on 2026-08-12.

## Failed verification command
The verification command assumed `GET /api/v1/qr-codes` returned either an array or an object with `.items`. PowerShell printed no rows.

## Interpretation
Blank table output is not evidence that QR data is missing. The command assumed a response shape that has not yet been verified against the currently running API.

## Safe next action
Run only:

```powershell
Invoke-RestMethod "http://127.0.0.1:3550/api/v1/qr-codes" | ConvertTo-Json -Depth 6
```

This is read-only. Inspect the raw JSON response and then derive the correct list command from the actual response contract.

## Safety
Do not restart services, deploy Worker code, modify DBs, or touch the working Timetable/Sheet/Test modules during this check.
