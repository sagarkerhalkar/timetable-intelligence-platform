const DEFAULT_ORIGIN = "https://nexttoppers.sagarkerhalkar.com";

function publicOrigin(request) {
  return new URL(request.url).origin;
}

function rewriteHeaderValue(value, fromOrigin, toOrigin) {
  if (!value) return value;
  return value.split(fromOrigin).join(toOrigin);
}

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    const originBase = String(env.ORIGIN_BASE || DEFAULT_ORIGIN).replace(/\/+$/, "");
    const origin = new URL(originBase);
    const pub = publicOrigin(request);

    if (incoming.pathname === "/__nexttoppers_health") {
      return Response.json({
        ok: true,
        service: "NextToppers QR Gateway",
        public_origin: pub,
        origin_hidden_from_qr: true
      }, {
        headers: {
          "cache-control": "no-store",
          "x-nexttoppers-qr-gateway": "1"
        }
      });
    }

    if (incoming.pathname === "/__nexttoppers_origin_check") {
      try {
        const probe = await fetch(new URL("/", origin), {
          method: "GET",
          redirect: "manual",
          headers: {"user-agent": "NextToppers-QR-Gateway-Origin-Check/1.0"}
        });
        return Response.json({
          ok: probe.status >= 200 && probe.status < 500,
          origin_status: probe.status,
          gateway: pub
        }, {
          status: probe.status >= 200 && probe.status < 500 ? 200 : 502,
          headers: {"cache-control": "no-store"}
        });
      } catch (error) {
        return Response.json({ok:false,error:"origin_unreachable"}, {
          status: 502,
          headers: {"cache-control": "no-store"}
        });
      }
    }

    if (incoming.pathname === "/") {
      return new Response("NextToppers QR Gateway", {
        status: 200,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store",
          "x-nexttoppers-qr-gateway": "1"
        }
      });
    }

    const upstreamUrl = new URL(incoming.pathname + incoming.search, origin);
    const headers = new Headers(request.headers);
    headers.set("x-forwarded-host", incoming.host);
    headers.set("x-forwarded-proto", "https");
    headers.set("x-nexttoppers-public-origin", pub);
    headers.set("x-nexttoppers-qr-gateway", "1");
    headers.delete("host");

    const init = {method: request.method, headers, redirect: "manual"};
    if (!["GET", "HEAD"].includes(request.method.toUpperCase())) init.body = request.body;

    let upstream;
    try {
      upstream = await fetch(upstreamUrl, init);
    } catch (error) {
      return Response.json({ok:false,error:"origin_fetch_failed"}, {
        status: 502,
        headers: {"cache-control":"no-store","x-nexttoppers-qr-gateway":"1"}
      });
    }

    const outHeaders = new Headers(upstream.headers);
    outHeaders.set("x-nexttoppers-qr-gateway", "1");
    outHeaders.set("cache-control", "no-store");

    const location = outHeaders.get("location");
    if (location) {
      try {
        const loc = new URL(location, origin);
        if (loc.origin === origin.origin) {
          outHeaders.set("location", pub + loc.pathname + loc.search + loc.hash);
        }
      } catch {}
    }

    const allowOrigin = outHeaders.get("access-control-allow-origin");
    if (allowOrigin && allowOrigin.includes(origin.origin)) {
      outHeaders.set("access-control-allow-origin", rewriteHeaderValue(allowOrigin, origin.origin, pub));
    }

    const csp = outHeaders.get("content-security-policy");
    if (csp && csp.includes(origin.origin)) {
      outHeaders.set("content-security-policy", rewriteHeaderValue(csp, origin.origin, pub));
    }

    const contentType = (outHeaders.get("content-type") || "").toLowerCase();
    const canRewrite = contentType.includes("text/html") || contentType.includes("application/json") || contentType.includes("javascript") || contentType.includes("text/css") || contentType.includes("text/plain");

    if (canRewrite && request.method.toUpperCase() !== "HEAD") {
      let body = await upstream.text();
      body = body.split(origin.origin).join(pub);
      body = body.split(origin.origin.replace(/\//g, "\\/")).join(pub.replace(/\//g, "\\/"));
      outHeaders.delete("content-length");
      outHeaders.delete("content-encoding");
      return new Response(body, {status: upstream.status, statusText: upstream.statusText, headers: outHeaders});
    }

    return new Response(upstream.body, {status: upstream.status, statusText: upstream.statusText, headers: outHeaders});
  }
};
