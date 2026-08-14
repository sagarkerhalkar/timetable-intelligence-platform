# 2026-08-14 - Preserve existing QR images while moving public scans to workers.dev

## Requirement
User does not want to regenerate or replace already-created/printed QR images, but wants scans to move to the new public Worker host `https://q.nexttoppers.workers.dev`.

## Constraint
The exact QR bitmap permanently encodes its original URL. Therefore a scanner preview can still reveal the originally encoded hostname. The bitmap cannot decode to a different URL without changing the image.

## Compatible solution
Keep the original QR image and use a Cloudflare Single Redirect on the old public QR hostname only for `/q/*` requests. Redirect browser/scanner requests to the Worker while preserving path and query string.

Current Worker gateway already sends header `x-nexttoppers-qr-gateway: 1` on its upstream request to the old origin. The Cloudflare redirect must exclude requests carrying this header to avoid an origin/Worker redirect loop.

Recommended Cloudflare filter expression:

```
(http.host eq "nexttoppers.sagarkerhalkar.com" and starts_with(http.request.uri.path, "/q/") and not any(http.request.headers["x-nexttoppers-qr-gateway"][*] eq "1"))
```

Dynamic target expression:

```
concat("https://q.nexttoppers.workers.dev", http.request.uri.path)
```

Preserve query string: enabled.
Initial status: 302 for safe acceptance testing. Consider 301 only after acceptance.

## Behavior
- Existing QR bitmap remains unchanged.
- Scanner decodes original URL because it is physically encoded in the QR.
- After the user opens it, Cloudflare immediately redirects to the Worker URL.
- Worker upstream calls bypass the redirect using the gateway header, so the Worker can still reach the existing origin and current analytics/redirect logic.
- Non-QR pages on the old hostname are unaffected because the rule is restricted to `/q/*`.
- New QR codes continue to use the Worker URL directly.

## Acceptance
1. Scan an existing printed QR.
2. Confirm it still works without regenerating the image.
3. After opening, browser should move to `q.nexttoppers.workers.dev` before the final destination.
4. Confirm QR analytics still increment.
5. Confirm normal timetable/app routes on the old hostname do not redirect.

## Safety note
Do not create a blanket redirect for the entire old hostname. That would affect the timetable application and can also create a Worker-origin loop.
