const DEFAULT_API_BASE = "https://nexttoppers.sagarkerhalkar.com/backend";
const PUBLIC_NAME = "NextToppers";

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

async function resolveQr(apiBase, slug) {
  const response = await fetch(`${apiBase}/api/v1/qr-fast/${encodeURIComponent(slug)}/resolve`, {
    method: "GET",
    headers: {"accept":"application/json", "x-nexttoppers-qr-gateway":"fast-v1"},
    redirect: "manual",
    cache: "no-store",
  });
  let body = null;
  try { body = await response.json(); } catch {}
  return {response, body};
}

function errorPage(status, message) {
  const safe = String(message || "This QR is unavailable.").replace(/[<>&]/g, "");
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${PUBLIC_NAME} QR</title></head><body style="font-family:system-ui;margin:0;display:grid;place-items:center;min-height:100vh;background:#f8fafc;color:#111827"><main style="text-align:center;padding:28px"><div style="font-weight:900;font-size:24px">NextToppers</div><p>${safe}</p></main></body></html>`, {
    status,
    headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","x-ntqr-fast":"1"}
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
  const delay = Math.max(120, Math.min(5000, Number(exp.redirect_delay_ms || 650)));
  const asset = exp.asset_id ? `/__ntqr_asset/${encodeURIComponent(exp.asset_id)}` : "";
  const logoScale = Math.max(15, Math.min(65, Number(exp.logo_scale_percent || 28)));
  const imageScale = Math.max(35, Math.min(100, Number(exp.image_scale_percent || 100)));
  const fit = exp.image_fit === "contain" ? "contain" : "cover";
  const visual = mode === "page" && asset
    ? `<img class="page-img" src="${asset}" alt="" decoding="async" fetchpriority="high">`
    : `<div class="card">${mode === "logo" && asset ? `<img class="logo-img" src="${asset}" alt="NextToppers">` : `<div class="nt">NT</div>`}<h1>${title}</h1><p>${message}</p>${identityEmail ? `<form id="emailForm"><input id="email" type="email" autocomplete="email" placeholder="name@example.com" required><button>Continue</button></form>` : `<div class="loader"><i></i></div>`}</div>`;

  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex,nofollow"><title>NextToppers</title><style>
*{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;background:${bg};color:#111827}body{min-height:100vh;display:grid;place-items:center;overflow:hidden}.card{text-align:center;width:min(92vw,420px);padding:28px}.nt{width:78px;height:78px;border-radius:24px;margin:0 auto 18px;display:grid;place-items:center;font-size:29px;font-weight:900;color:white;background:${accent};box-shadow:0 18px 48px rgba(15,23,42,.16)}.logo-img{display:block;max-width:${logoScale}vw;max-height:${logoScale}vh;width:auto;height:auto;margin:0 auto 18px;object-fit:contain}.page-img{width:${imageScale}vw;height:${imageScale}vh;max-width:100vw;max-height:100vh;object-fit:${fit};display:block}h1{font-size:23px;margin:8px 0}p{margin:0 0 18px;color:#475569}.loader{height:5px;background:#e2e8f0;border-radius:99px;overflow:hidden}.loader i{display:block;width:38%;height:100%;background:${accent};border-radius:99px;animation:m .55s ease-in-out infinite alternate}@keyframes m{from{transform:translateX(-20%)}to{transform:translateX(190%)}}form{display:grid;gap:10px}input,button{font:inherit;border-radius:12px;padding:13px 14px}input{border:1px solid #cbd5e1;background:white}button{border:0;background:${accent};color:white;font-weight:800}
</style></head><body>${visual}<script>
(()=>{const TARGET=${target},SLUG=${slugJson},QUERY=${queryJson},DELAY=${delay},EMAIL=${identityEmail ? "true":"false"};
function id(){try{let v=localStorage.getItem("ntqr_browser_id");if(!v){v=(crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2)+Date.now().toString(36));localStorage.setItem("ntqr_browser_id",v)}return v}catch{return Math.random().toString(36).slice(2)}}
function eventId(){return crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2)+Date.now().toString(36)}
function payload(email){return {event_id:eventId(),visitor_id:id(),user_agent:navigator.userAgent||"",language:navigator.language||"",timezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||""),referrer:document.referrer||"",query:QUERY,scanner_email:email||"",client_platform:navigator.platform||"",device_model:"",screen_width:screen.width||null,screen_height:screen.height||null,telemetry:{hardwareConcurrency:navigator.hardwareConcurrency||null,deviceMemory:navigator.deviceMemory||null,maxTouchPoints:navigator.maxTouchPoints||0,colorDepth:screen.colorDepth||null,pixelRatio:devicePixelRatio||1,online:navigator.onLine}}}
function send(email){const data=JSON.stringify(payload(email));let queued=false;try{queued=navigator.sendBeacon("/__ntqr_scan/"+encodeURIComponent(SLUG),new Blob([data],{type:"text/plain;charset=UTF-8"}))}catch{}if(!queued){try{fetch("/__ntqr_scan/"+encodeURIComponent(SLUG),{method:"POST",headers:{"content-type":"text/plain;charset=UTF-8"},body:data,keepalive:true}).catch(()=>{})}catch{}}}
function go(email){send(email);setTimeout(()=>location.replace(TARGET),EMAIL?40:DELAY)}
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
  const logPromise = fetch(`${apiBase}/api/v1/qr-fast/${encodeURIComponent(slug)}/confirm`, {
    method:"POST",
    headers:{"content-type":"application/json","x-nexttoppers-qr-gateway":"fast-v1"},
    body:JSON.stringify(payload),
    redirect:"manual",
  }).catch(()=>null);
  ctx.waitUntil(logPromise);
  return new Response(null,{status:204,headers:{"cache-control":"no-store","x-ntqr-fast":"1"}});
}

async function handleAsset(request, env, assetId) {
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(assetId)) return new Response("Not found",{status:404});
  const apiBase = cleanBase(env.API_BASE);
  const response = await fetch(`${apiBase}/api/v1/qr-assets/${encodeURIComponent(assetId)}`, {
    headers:{"accept":request.headers.get("accept") || "image/*","x-nexttoppers-qr-gateway":"fast-v1"},
    redirect:"manual",
    cf:{cacheEverything:true,cacheTtl:86400},
  });
  const headers = new Headers(response.headers);
  headers.set("cache-control","public, max-age=86400");
  headers.set("x-ntqr-fast","1");
  return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/__ntqr_health") {
      return Response.json({ok:true,service:"NextToppers QR Fast Edge",fast_path:true,public_origin:url.origin},{headers:{"cache-control":"no-store","x-ntqr-fast":"1"}});
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
    const apiBase = cleanBase(env.API_BASE);
    const started = Date.now();
    let resolved;
    try { resolved = await resolveQr(apiBase,slug); } catch { return errorPage(502,"QR service is temporarily unavailable."); }
    const resolveMs = Math.max(0,Date.now()-started);
    if (!resolved.response.ok || !resolved.body?.ok) {
      return errorPage(resolved.response.status || 502, resolved.body?.detail || "QR code is unavailable.");
    }
    if (resolved.body.tracking_mode === "direct" && /^https?:\/\//i.test(String(resolved.body.target_url||""))) {
      const headers = new Headers({"location":String(resolved.body.target_url),"cache-control":"no-store","x-ntqr-fast":"1","server-timing":`resolve;dur=${resolveMs}`});
      return new Response(null,{status:302,headers});
    }
    const html = scanHtml(resolved.body,slug,request.url);
    return new Response(html,{status:200,headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","x-ntqr-fast":"1","server-timing":`resolve;dur=${resolveMs}`}});
  }
};
