const DEFAULT_API_BASE = "https://nexttoppers.sagarkerhalkar.com/backend";
const PUBLIC_NAME = "NextToppers";
const KV_CACHE_TTL = 30;

function cleanBase(value) {
  return String(value || DEFAULT_API_BASE).replace(/\/+$/, "");
}

function jsonForScript(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
}

function slugFromPath(pathname) {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 2 && parts[0] === "q") return decodeURIComponent(parts[1]);
  if (parts.length === 1 && !parts[0].startsWith("__")) return decodeURIComponent(parts[0]);
  return null;
}

function edgeData(request) {
  const cf = request.cf || {};
  const keys = ["colo","country","city","region","regionCode","continent","timezone","asn","asOrganization","httpProtocol","tlsVersion","clientTcpRtt","clientQuicRtt"];
  const out = {};
  for (const key of keys) if (cf[key] !== undefined && cf[key] !== null) out[key] = cf[key];
  return out;
}

function validRoute(qr) {
  return qr && typeof qr === "object" &&
    /^[A-Za-z0-9_-]{2,80}$/.test(String(qr.slug || "")) &&
    typeof qr.target_url === "string";
}

async function getRouteFromKv(env, slug) {
  if (!env.QR_EDGE) return null;
  try {
    const value = await env.QR_EDGE.get(`qr:${slug}`, {type:"json", cacheTtl:KV_CACHE_TTL});
    return validRoute(value) ? value : null;
  } catch {
    return null;
  }
}

async function resolveQr(apiBase, slug) {
  const response = await fetch(`${apiBase}/api/v1/qr-fast/${encodeURIComponent(slug)}/resolve`, {
    method: "GET",
    headers: {"accept":"application/json", "x-nexttoppers-qr-gateway":"edge-kv-fallback"},
    redirect: "manual",
    cache: "no-store",
  });
  let body = null;
  try { body = await response.json(); } catch {}
  return {response, body};
}

async function putRoute(env, route) {
  if (!env.QR_EDGE || !validRoute(route)) return;
  await env.QR_EDGE.put(`qr:${route.slug}`, JSON.stringify(route));
}

function errorPage(status, message) {
  const safe = String(message || "This QR is unavailable.").replace(/[<>&]/g, "");
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${PUBLIC_NAME} QR</title></head><body style="font-family:system-ui;margin:0;display:grid;place-items:center;min-height:100vh;background:#f8fafc;color:#111827"><main style="text-align:center;padding:28px"><div style="font-weight:900;font-size:24px">NextToppers</div><p>${safe}</p></main></body></html>`, {
    status,
    headers: {"content-type":"text/html; charset=utf-8","cache-control":"no-store","x-ntqr-fast":"2","x-ntqr-source":"edge-kv"}
  });
}

function scanHtml(qr, slug, requestUrl) {
  const exp = qr.experience || {};
  const target = jsonForScript(String(qr.target_url || ""));
  const slugJson = jsonForScript(slug);
  const queryJson = jsonForScript(new URL(requestUrl).search || "");
  const identityEmail = qr.identity_mode === "email";
  const mode = ["brand","logo","page"].includes(exp.mode) ? exp.mode : "brand";
  const title = String(exp.title || "NextToppers").replace(/[<>&]/g, "");
  const message = String(exp.message || "Opening your content…").replace(/[<>&]/g, "");
  const accent = /^#[0-9a-f]{3,8}$/i.test(String(exp.accent_color || "")) ? exp.accent_color : "#2455FF";
  const bg = /^#[0-9a-f]{3,8}$/i.test(String(exp.background_color || "")) ? exp.background_color : "#F8FAFC";
  const delay = Math.max(0, Math.min(120, Number(exp.redirect_delay_ms || 0)));
  const asset = exp.asset_id ? `/__ntqr_asset/${encodeURIComponent(exp.asset_id)}` : "";
  const logoScale = Math.max(15, Math.min(65, Number(exp.logo_scale_percent || 28)));
  const imageScale = Math.max(35, Math.min(100, Number(exp.image_scale_percent || 100)));
  const fit = exp.image_fit === "contain" ? "contain" : "cover";
  const visual = mode === "page" && asset
    ? `<img class="page-img" src="${asset}" alt="" decoding="async" fetchpriority="high">`
    : `<div class="card">${mode === "logo" && asset ? `<img class="logo-img" src="${asset}" alt="NextToppers" decoding="async">` : `<div class="nt">NT</div>`}<h1>${title}</h1><p>${message}</p>${identityEmail ? `<form id="emailForm"><input id="email" type="email" autocomplete="email" placeholder="name@example.com" required><button>Continue</button></form>` : `<div class="loader"><i></i></div>`}</div>`;

  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex,nofollow"><title>NextToppers</title><style>
*{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;background:${bg};color:#111827}body{min-height:100vh;display:grid;place-items:center;overflow:hidden}.card{text-align:center;width:min(92vw,420px);padding:22px}.nt{width:72px;height:72px;border-radius:22px;margin:0 auto 14px;display:grid;place-items:center;font-size:27px;font-weight:900;color:white;background:${accent};box-shadow:0 14px 38px rgba(15,23,42,.14)}.logo-img{display:block;max-width:${logoScale}vw;max-height:${logoScale}vh;width:auto;height:auto;margin:0 auto 14px;object-fit:contain}.page-img{width:${imageScale}vw;height:${imageScale}vh;max-width:100vw;max-height:100vh;object-fit:${fit};display:block}h1{font-size:22px;margin:7px 0}p{margin:0 0 14px;color:#475569}.loader{height:4px;background:#e2e8f0;border-radius:99px;overflow:hidden}.loader i{display:block;width:44%;height:100%;background:${accent};border-radius:99px;animation:m .35s ease-in-out infinite alternate}@keyframes m{from{transform:translateX(-30%)}to{transform:translateX(170%)}}form{display:grid;gap:10px}input,button{font:inherit;border-radius:12px;padding:13px 14px}input{border:1px solid #cbd5e1;background:white}button{border:0;background:${accent};color:white;font-weight:800}
</style></head><body>${visual}<script>
(()=>{const TARGET=${target},SLUG=${slugJson},QUERY=${queryJson},DELAY=${delay},EMAIL=${identityEmail ? "true":"false"};
function id(){try{let v=localStorage.getItem("ntqr_browser_id");if(!v){v=(crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2)+Date.now().toString(36));localStorage.setItem("ntqr_browser_id",v)}return v}catch{return Math.random().toString(36).slice(2)}}
function eventId(){return crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2)+Date.now().toString(36)}
function payload(email){return {event_id:eventId(),visitor_id:id(),user_agent:navigator.userAgent||"",language:navigator.language||"",timezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||""),referrer:document.referrer||"",query:QUERY,scanner_email:email||"",client_platform:navigator.platform||"",device_model:"",screen_width:screen.width||null,screen_height:screen.height||null,telemetry:{hardwareConcurrency:navigator.hardwareConcurrency||null,deviceMemory:navigator.deviceMemory||null,maxTouchPoints:navigator.maxTouchPoints||0,colorDepth:screen.colorDepth||null,pixelRatio:devicePixelRatio||1,online:navigator.onLine}}}
function send(email){const data=JSON.stringify(payload(email));let queued=false;try{queued=navigator.sendBeacon("/__ntqr_scan/"+encodeURIComponent(SLUG),new Blob([data],{type:"text/plain;charset=UTF-8"}))}catch{}if(!queued){try{fetch("/__ntqr_scan/"+encodeURIComponent(SLUG),{method:"POST",headers:{"content-type":"text/plain;charset=UTF-8"},body:data,keepalive:true}).catch(()=>{})}catch{}}}
function go(email){send(email);if(EMAIL){setTimeout(()=>location.replace(TARGET),40)}else if(DELAY>0){setTimeout(()=>location.replace(TARGET),DELAY)}else{location.replace(TARGET)}}
if(EMAIL){const f=document.getElementById("emailForm");f.addEventListener("submit",e=>{e.preventDefault();const el=document.getElementById("email");if(el.checkValidity())go(el.value.trim())})}else{go("")}
})();</script></body></html>`;
}

async function handleBeacon(request, env, ctx, slug) {
  if (request.method !== "POST") return new Response("Method Not Allowed", {status:405});
  const length = Number(request.headers.get("content-length") || "0");
  if (length > 16384) return new Response("Payload too large", {status:413});
  const raw = (await request.text()).slice(0, 16384);
  let payload = {};
  try { payload = JSON.parse(raw); } catch { return new Response("Bad request", {status:400}); }
  payload.edge = edgeData(request);
  payload.user_agent = String(payload.user_agent || request.headers.get("user-agent") || "").slice(0,700);
  const apiBase = cleanBase(env.API_BASE);
  ctx.waitUntil(
    fetch(`${apiBase}/api/v1/qr-fast/${encodeURIComponent(slug)}/confirm`, {
      method:"POST",
      headers:{"content-type":"application/json","x-nexttoppers-qr-gateway":"edge-kv-analytics"},
      body:JSON.stringify(payload),
      redirect:"manual",
    }).catch(()=>null)
  );
  return new Response(null,{status:204,headers:{"cache-control":"no-store","x-ntqr-fast":"2","x-ntqr-source":"edge-kv"}});
}

async function handleAsset(request, env, assetId) {
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(assetId)) return new Response("Not found",{status:404});
  const apiBase = cleanBase(env.API_BASE);
  const response = await fetch(`${apiBase}/api/v1/qr-assets/${encodeURIComponent(assetId)}`, {
    headers:{"accept":request.headers.get("accept") || "image/*","x-nexttoppers-qr-gateway":"edge-kv-asset"},
    redirect:"manual",
    cf:{cacheEverything:true,cacheTtl:86400},
  });
  const headers = new Headers(response.headers);
  headers.set("cache-control","public, max-age=86400");
  headers.set("x-ntqr-fast","2");
  return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}

function safeRouteInput(value) {
  if (!value || typeof value !== "object") return null;
  const slug = String(value.slug || "").trim();
  if (!/^[A-Za-z0-9_-]{2,80}$/.test(slug)) return null;
  const target = String(value.target_url || "").trim();
  const experience = value.experience && typeof value.experience === "object" ? value.experience : {};
  return {
    ok:true,
    id:String(value.id || ""),
    slug,
    name:String(value.name || "NextToppers QR").slice(0,200),
    qr_type:String(value.qr_type || "url").slice(0,40),
    tracking_mode:String(value.tracking_mode || "tracked").slice(0,20),
    identity_mode:String(value.identity_mode || "anonymous").slice(0,20),
    target_url:target.slice(0,8000),
    active:Boolean(value.active),
    experience:{
      mode:["brand","logo","page"].includes(String(experience.mode || "")) ? String(experience.mode) : "brand",
      asset_id:experience.asset_id ? String(experience.asset_id).slice(0,80) : null,
      title:String(experience.title || "NextToppers").slice(0,80),
      message:String(experience.message || "Opening your content…").slice(0,160),
      accent_color:String(experience.accent_color || "#2455FF").slice(0,24),
      background_color:String(experience.background_color || "#F8FAFC").slice(0,24),
      redirect_delay_ms:Math.max(0,Math.min(120,Number(experience.redirect_delay_ms || 0))),
      logo_scale_percent:Math.max(15,Math.min(65,Number(experience.logo_scale_percent || 28))),
      image_fit:experience.image_fit === "contain" ? "contain" : "cover",
      image_scale_percent:Math.max(35,Math.min(100,Number(experience.image_scale_percent || 100))),
    },
    updated_at:String(value.updated_at || "").slice(0,80),
  };
}

async function handleAdminSync(request, env) {
  if (request.method !== "POST") return new Response("Method Not Allowed",{status:405});
  if (!env.QR_EDGE || !env.NEXTTOPPERS_EDGE_SYNC_SECRET) {
    return Response.json({ok:false,error:"edge_storage_not_configured"},{status:503});
  }
  const supplied = request.headers.get("x-ntqr-sync-secret") || "";
  if (supplied !== env.NEXTTOPPERS_EDGE_SYNC_SECRET) {
    return Response.json({ok:false,error:"forbidden"},{status:403});
  }
  const length = Number(request.headers.get("content-length") || "0");
  if (length > 5_000_000) return Response.json({ok:false,error:"payload_too_large"},{status:413});
  let body;
  try { body = await request.json(); } catch { return Response.json({ok:false,error:"bad_json"},{status:400}); }
  const mode = body && body.mode === "delta" ? "delta" : "replace";
  const inputRoutes = Array.isArray(body?.routes) ? body.routes : [];
  const routes = inputRoutes.map(safeRouteInput).filter(Boolean);
  const deleteInput = Array.isArray(body?.deletes) ? body.deletes : [];
  let deletes = deleteInput.map(v=>String(v||"").trim()).filter(v=>/^[A-Za-z0-9_-]{2,80}$/.test(v));

  if (mode === "replace") {
    let oldIndex = [];
    try {
      const previous = await env.QR_EDGE.get("__ntqr_index",{type:"json"});
      if (Array.isArray(previous)) oldIndex = previous.map(v=>String(v));
    } catch {}
    const next = new Set(routes.map(r=>r.slug));
    deletes = oldIndex.filter(slug=>/^[A-Za-z0-9_-]{2,80}$/.test(slug) && !next.has(slug));
  }

  for (const route of routes) {
    await env.QR_EDGE.put(`qr:${route.slug}`,JSON.stringify(route));
  }
  for (const slug of deletes) {
    await env.QR_EDGE.delete(`qr:${slug}`);
  }

  if (mode === "replace") {
    await env.QR_EDGE.put("__ntqr_index",JSON.stringify(routes.map(r=>r.slug)));
  } else if (routes.length || deletes.length) {
    let index = [];
    try {
      const existing = await env.QR_EDGE.get("__ntqr_index",{type:"json"});
      if (Array.isArray(existing)) index = existing.map(v=>String(v));
    } catch {}
    const set = new Set(index.filter(v=>/^[A-Za-z0-9_-]{2,80}$/.test(v)));
    for (const route of routes) set.add(route.slug);
    for (const slug of deletes) set.delete(slug);
    await env.QR_EDGE.put("__ntqr_index",JSON.stringify([...set].sort()));
  }

  return Response.json(
    {ok:true,mode,upserts:routes.length,deletes:deletes.length},
    {headers:{"cache-control":"no-store","x-ntqr-fast":"2","x-ntqr-source":"edge-kv"}}
  );
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/" || url.pathname === "/__ntqr_health") {
      return Response.json(
        {ok:true,service:"NextToppers QR Edge KV",fast_path:true,edge_kv:Boolean(env.QR_EDGE),public_origin:url.origin},
        {headers:{"cache-control":"no-store","x-ntqr-fast":"2","x-ntqr-source":"edge-kv"}}
      );
    }

    if (url.pathname === "/__ntqr_admin/sync") {
      return handleAdminSync(request,env);
    }

    if (url.pathname.startsWith("/__ntqr_scan/")) {
      const slug = decodeURIComponent(url.pathname.slice("/__ntqr_scan/".length));
      return handleBeacon(request,env,ctx,slug);
    }

    if (url.pathname.startsWith("/__ntqr_asset/")) {
      const assetId = decodeURIComponent(url.pathname.slice("/__ntqr_asset/".length));
      return handleAsset(request,env,assetId);
    }

    const slug = slugFromPath(url.pathname);
    if (!slug || !/^[A-Za-z0-9_-]{2,80}$/.test(slug)) return errorPage(404,"QR code not found.");

    const kvStarted = Date.now();
    let qr = await getRouteFromKv(env,slug);
    const kvMs = Math.max(0,Date.now()-kvStarted);
    let source = "kv";

    if (!qr) {
      source = "origin-fallback";
      const apiBase = cleanBase(env.API_BASE);
      let resolved;
      try { resolved = await resolveQr(apiBase,slug); } catch { return errorPage(502,"QR service is temporarily unavailable."); }
      if (!resolved.response.ok || !resolved.body?.ok) {
        return errorPage(resolved.response.status || 502, resolved.body?.detail || "QR code is unavailable.");
      }
      qr = safeRouteInput(resolved.body);
      if (!qr) return errorPage(502,"QR route data is invalid.");
      ctx.waitUntil(putRoute(env,qr).catch(()=>null));
    }

    if (!qr.active) return errorPage(410,"QR code is inactive.");
    if (!/^https?:\/\//i.test(String(qr.target_url || ""))) return errorPage(422,"QR destination is invalid.");

    if (qr.tracking_mode === "direct") {
      const headers = new Headers({
        "location":String(qr.target_url),
        "cache-control":"no-store",
        "x-ntqr-fast":"2",
        "x-ntqr-source":source,
        "server-timing":`kv;dur=${kvMs}`,
      });
      return new Response(null,{status:302,headers});
    }

    const html = scanHtml(qr,slug,request.url);
    return new Response(html,{
      status:200,
      headers:{
        "content-type":"text/html; charset=utf-8",
        "cache-control":"no-store",
        "x-ntqr-fast":"2",
        "x-ntqr-source":source,
        "server-timing":`kv;dur=${kvMs}`,
      },
    });
  }
};
