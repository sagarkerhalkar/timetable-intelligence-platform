# NextToppers QR branch

Purpose: keep the public hostname `https://nexttoppers.sagarkerhalkar.com` unchanged while removing the parent-domain text from normal QR UI and making the web runtime production-first for faster loading.

## Branding behavior

- QR product label: `NextToppers QR`.
- QR browser/page metadata: `NextToppers QR` where Next.js metadata applies.
- New QR loading experience default: title `NextToppers`, message `Opening your content...`.
- My QR Codes does not print the full public hostname in the normal table/card view. It shows `NextToppers QR` instead.
- `Copy QR Link` and `Open NextToppers QR` still use the real tracked URL so QR tracking continues to work.
- `Copy Source Link` continues to copy the original destination URL.
- The real hostname cannot be removed from a normal browser address bar while the site continues to use `nexttoppers.sagarkerhalkar.com`.

## Performance behavior

- Production runtime uses `next build` followed by `next start` on port 3500.
- Do not use `next dev` for the public production URL.
- Keep the existing same-origin `/backend` bridge to API 3550.
- Cloudflare Tunnel continues to map `nexttoppers.sagarkerhalkar.com` to `http://127.0.0.1:3500`.
- Cloudflare may cache static Next.js assets, but `/backend/*`, `/q/*`, analytics/API and other dynamic routes must not be cached as static content.

## Data safety

This branch does not change the production SQLite database. The authoritative DB remains `D:\timetable-intelligence-platform\services\api\data\timetable.db`. Port 3457 remains protected.

## Branch model

- `working-current`: frozen safety branch.
- `nexttoppersqr`: branding/performance branch.
- stable `v1`: untouched until Windows acceptance succeeds.
