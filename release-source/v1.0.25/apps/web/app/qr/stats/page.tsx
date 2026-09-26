"use client";

import Link from "next/link";
import { CSSProperties, ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PaginationControls } from "../../../components/pagination-controls";
import { QrProductNav } from "../../../components/qr-product-nav";
import { paginateItems } from "../../../lib/pagination";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type QrCodeRecord = {
  id: string; name: string; slug: string; target_url: string; active: boolean;
  qr_type: string; tracking_mode: string; identity_mode: string;
  total_scans: number; unique_visitors: number; unique_emails: number; country_count: number; legacy_scans: number;
};

type QrScanRecord = {
  id: number; qr_id: string; qr_name: string; scanned_at: string;
  country: string; device_type: string; browser: string; operating_system: string;
  device_model: string; device_id: string; scanner_email: string;
  platform: string; source_confidence: string; referrer_host: string; language:string; timezone:string; screen_resolution:string; client_platform:string;
  browser_version:string; platform_version:string; architecture:string; bitness:string; device_memory_gb:number|null; hardware_concurrency:number|null;
  max_touch_points:number|null; pixel_ratio:number|null; viewport:string; viewport_width:number|null; viewport_height:number|null; color_depth:number|null; connection:string; network_quality:string; form_factors:string;
  screen_orientation:string; browser_vendor:string; cookies_enabled:boolean|null; standalone:boolean|null; input_capability:string; color_gamut:string; languages:string; timezone_offset_minutes:number|null;
};

type DeviceSummary = { device_id:string; scans:number; first_seen:string; last_seen:string; device_type:string; operating_system:string; browser:string; device_model:string; scanner_email:string; client_platform:string; language:string; timezone:string; screen_resolution:string; countries:number; qr_codes:number;
  browser_version:string; platform_version:string; architecture:string; bitness:string; device_memory_gb:number|null; hardware_concurrency:number|null;
  max_touch_points:number|null; pixel_ratio:number|null; viewport:string; viewport_width:number|null; viewport_height:number|null; color_depth:number|null; connection:string; network_quality:string; form_factors:string;
  screen_orientation:string; browser_vendor:string; cookies_enabled:boolean|null; standalone:boolean|null; input_capability:string; color_gamut:string; languages:string; timezone_offset_minutes:number|null };
type Analytics = {
  total_qr_codes: number; active_qr_codes: number; total_scans: number; unique_visitors: number; unique_emails:number; identified_scans:number; anonymous_scans:number;
  scans_today: number; scans_7days: number; scans_30days: number; bot_scans: number; legacy_scans: number;
  countries: Record<string, number>; devices: Record<string, number>; browsers: Record<string, number>;
  operating_systems: Record<string, number>; device_models:Record<string,number>; memory_classes:Record<string,number>; cpu_cores:Record<string,number>; connection_types:Record<string,number>; platforms: Record<string, number>; attribution_confidence: Record<string, number>;
  daily: Record<string, number>; top_devices:DeviceSummary[]; recent_scans: QrScanRecord[];
};

const emptyAnalytics: Analytics = {
  total_qr_codes:0, active_qr_codes:0, total_scans:0, unique_visitors:0, unique_emails:0, identified_scans:0, anonymous_scans:0, scans_today:0,
  scans_7days:0, scans_30days:0, bot_scans:0, legacy_scans:0, countries:{}, devices:{}, browsers:{}, operating_systems:{}, device_models:{}, memory_classes:{}, cpu_cores:{}, connection_types:{}, platforms:{}, attribution_confidence:{}, daily:{}, top_devices:[], recent_scans:[]
};

function countryName(code: string) {
  if (!code || code === "Unknown") return "Unknown";
  try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code) || code; } catch { return code; }
}
function host(url: string) { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; } }
function indiaTime(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.valueOf()) ? value : new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" }).format(d);
}
function indiaDayKey(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const value = (part: string) => parts.find((x) => x.type === part)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}
function days30(daily: Record<string, number>) {
  return Array.from({ length: 30 }, (_, index) => {
    const d = new Date(Date.now() - (29 - index) * 86400000);
    const key = indiaDayKey(d);
    const label = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short" }).format(d);
    return { key, label, count: daily[key] || 0 };
  });
}

function LineChart({ rows }: { rows: Array<{ key: string; label: string; count: number }> }) {
  const max = Math.max(1, ...rows.map((x) => x.count));
  const divisor = Math.max(1, rows.length - 1);
  const points = rows.map((x, i) => `${(i / divisor) * 100},${88 - (x.count / max) * 68}`).join(" ");
  return <div className="qrfy-line-chart">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="30-day verified scan trend">
      <defs><linearGradient id="qrfyArea20" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2f5cff" stopOpacity=".24" /><stop offset="100%" stopColor="#2f5cff" stopOpacity="0" /></linearGradient></defs>
      <polygon points={`0,100 ${points} 100,100`} fill="url(#qrfyArea20)" />
      <polyline points={points} fill="none" stroke="#2f5cff" strokeWidth="2.2" vectorEffect="non-scaling-stroke" />
    </svg>
    <div className="qrfy-chart-labels"><span>{rows[0]?.label}</span><span>{rows[Math.floor(rows.length / 2)]?.label}</span><span>{rows.at(-1)?.label}</span></div>
  </div>;
}

function Bars({ data, country = false, empty = "No verified scan data yet." }: { data: Record<string, number>; country?: boolean; empty?: string }) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = Math.max(1, ...rows.map(([, v]) => v));
  return <div className="qrfy-stat-bars">
    {rows.map(([label, count], i) => <div key={label} className="qrfy-stat-bar" style={{ "--delay": `${i * 55}ms` } as CSSProperties}>
      <div><strong>{country ? countryName(label) : label}</strong><span>{count.toLocaleString("en-IN")}</span></div>
      <i><b style={{ width: `${(count / max) * 100}%` }} /></i>
    </div>)}
    {!rows.length ? <div className="qrfy-no-data">{empty}</div> : null}
  </div>;
}

function confidenceLabel(value: string) {
  if (value === "tagged") return "Exact";
  if (value === "detected") return "Detected";
  return "Unknown";
}

function compactDeviceId(value:string){return value.replace(/^Device\s*/i,"").slice(0,10).toUpperCase()}
function deviceName(device:DeviceSummary){return [device.device_type,device.device_model||device.operating_system].filter(Boolean).join(" · ")}
function cleanBrowserVersion(value:string,browser:string){const parts=String(value||"").split(",").map(x=>x.trim()).filter(Boolean).filter(x=>!/not.?a.?brand/i.test(x));const preferred=parts.find(x=>/google chrome|microsoft edge|firefox|safari|opera/i.test(x))||parts.find(x=>new RegExp(browser,"i").test(x))||parts[0];return preferred||browser||"Unavailable"}
function cleanTimezone(value:string){return value==="Asia/Calcutta"?"Asia/Kolkata":value}
function cleanResolution(value:string){return String(value||"").replaceAll("×"," x ").replace(/\s+x\s+/g," x ")}
function detailText(value:string|number|null|undefined,fallback="Unavailable"){return value===null||value===undefined||value===""?fallback:String(value)}
function boolText(value:boolean|null){return value===null?"Unavailable":value?"Yes":"No"}

export default function QrStatsPage() {
  const [codes, setCodes] = useState<QrCodeRecord[]>([]);
  const [selected, setSelected] = useState("");
  const [ready, setReady] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics>(emptyAnalytics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [devicePage, setDevicePage] = useState(1);
  const [recentPage, setRecentPage] = useState(1);

  const load = useCallback(async (qrId: string) => {
    setLoading(true); setError("");
    try {
      const [codesResponse, analyticsResponse] = await Promise.all([
        fetch(`${PUBLIC_API_URL}/api/v1/qr-codes`, { cache: "no-store" }),
        fetch(`${PUBLIC_API_URL}/api/v1/qr-analytics${qrId ? `?qr_id=${encodeURIComponent(qrId)}` : ""}`, { cache: "no-store" })
      ]);
      if (!codesResponse.ok || !analyticsResponse.ok) throw new Error("Could not load QR statistics.");
      setCodes(await codesResponse.json() as QrCodeRecord[]);
      setAnalytics(await analyticsResponse.json() as Analytics);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load QR statistics."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    setSelected(new URLSearchParams(window.location.search).get("qr_id") || "");
    setReady(true);
  }, []);
  useEffect(() => { if (ready) void load(selected); }, [selected, ready, load]);

  const selectedCode = useMemo(() => codes.find((x) => x.id === selected) || null, [codes, selected]);
  const trend = useMemo(() => days30(analytics.daily), [analytics.daily]);
  const deviceData = useMemo(() => paginateItems(analytics.top_devices, devicePage, 6), [analytics.top_devices, devicePage]);
  const recentData = useMemo(() => paginateItems(analytics.recent_scans, recentPage, 15), [analytics.recent_scans, recentPage]);
  const topCodes = useMemo(() => [...codes].sort((a, b) => b.total_scans - a.total_scans).slice(0, 6), [codes]);
  const uniqueRate = analytics.total_scans ? Math.round((analytics.unique_visitors / analytics.total_scans) * 100) : 0;
  const tagged = analytics.attribution_confidence.tagged || 0;
  const detected = analytics.attribution_confidence.detected || 0;
  const unknown = analytics.attribution_confidence.unknown || 0;

  useEffect(() => { setDevicePage(1); setRecentPage(1); }, [selected]);
  useEffect(() => { if (devicePage !== deviceData.page) setDevicePage(deviceData.page); }, [devicePage, deviceData.page]);
  useEffect(() => { if (recentPage !== recentData.page) setRecentPage(recentData.page); }, [recentPage, recentData.page]);

  return <main className="qrfy-page qr-route-enter qr-stats-v23">
    <QrProductNav />
    <header className="qrfy-page-header">
      <div><p className="qrfy-kicker">Verified scan intelligence</p><h1>Statistics</h1><p>Verified scans, repeat-device intelligence, identity, country, browser, OS and source attribution in a cleaner global dashboard.</p></div>
      <div className="qrfy-header-actions"><a className="qrfy-button ghost" href={`${PUBLIC_API_URL}/api/v1/qr-scans/export.csv${selected ? `?qr_id=${selected}` : ""}`}>Export CSV</a><Link className="qrfy-button primary" href="/qr">＋ Create New</Link></div>
    </header>

    <section className="qrfy-panel qrfy-stats-filter">
      <label><span>QR code</span><select value={selected} onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelected(e.target.value)}><option value="">All QR codes · Global statistics</option>{codes.map(code => <option key={code.id} value={code.id}>{code.name}</option>)}</select></label>
      <div className="qrfy-live-status"><i /><div><strong>{selectedCode?.name || "All QR codes"}</strong><small>{selectedCode ? `${selectedCode.qr_type} · ${selectedCode.tracking_mode}` : `${analytics.active_qr_codes} active campaigns`}</small></div></div>
    </section>

    {error ? <div className="qrfy-toast error">{error}</div> : null}
    <section className="qr-data-quality">
      <div><strong>Verified analytics</strong><span>Main KPIs count only browser-confirmed scans. Link-preview bots and old direct redirects do not inflate the verified totals.</span></div>
      <div className="qr-quality-pills"><b>{analytics.total_scans.toLocaleString("en-IN")} verified</b>{analytics.legacy_scans > 0 ? <em>{analytics.legacy_scans.toLocaleString("en-IN")} legacy/unverified kept separately</em> : <em>0 legacy/unverified</em>}</div>
    </section>

    <section className="qrfy-stat-kpis qr-stat-kpis-v20">
      <article><span>Verified total scans</span><strong>{analytics.total_scans.toLocaleString("en-IN")}</strong><small>Confirmed browser executions</small></article>
      <article><span>Unique browsers/devices</span><strong>{analytics.unique_visitors.toLocaleString("en-IN")}</strong><small>{uniqueRate}% of verified scan volume</small></article>
      <article><span>Today</span><strong>{analytics.scans_today.toLocaleString("en-IN")}</strong><small>India calendar day</small></article>
      <article><span>Last 30 days</span><strong>{analytics.scans_30days.toLocaleString("en-IN")}</strong><small>Verified rolling activity</small></article>
      <article><span>Identified emails</span><strong>{analytics.unique_emails.toLocaleString("en-IN")}</strong><small>{analytics.identified_scans.toLocaleString("en-IN")} identified scans</small></article>
      <article><span>Anonymous scans</span><strong>{analytics.anonymous_scans.toLocaleString("en-IN")}</strong><small>No email required</small></article>
      <article><span>Countries</span><strong>{Object.keys(analytics.countries).length.toLocaleString("en-IN")}</strong><small>Cloudflare/browser-confirmed traffic</small></article>
      <article><span>Active QR</span><strong>{analytics.active_qr_codes}/{analytics.total_qr_codes}</strong><small>Campaign status</small></article>
    </section>

    <section className="qrfy-stats-grid qr-stats-grid-v20">
      <article className="qrfy-panel qrfy-chart-wide"><div className="qrfy-card-title"><div><span>SCAN ACTIVITY</span><h2>30-day verified trend</h2></div><b>{analytics.scans_30days.toLocaleString("en-IN")} scans</b></div><LineChart rows={trend} /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>LOCATION</span><h2>Countries</h2></div><b>{Object.keys(analytics.countries).length}</b></div><Bars data={analytics.countries} country /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>TECHNOLOGY</span><h2>Devices</h2></div><b>Verified</b></div><Bars data={analytics.devices} /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>TECHNOLOGY</span><h2>Browsers</h2></div><b>Verified</b></div><Bars data={analytics.browsers} /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>TECHNOLOGY</span><h2>Operating systems</h2></div><b>Verified</b></div><Bars data={analytics.operating_systems} /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>DEVICE INTELLIGENCE</span><h2>Device models</h2></div><b>When browser allows</b></div><Bars data={analytics.device_models} empty="Device model is hidden by this browser/device." /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>DEVICE CAPABILITY</span><h2>Memory class</h2></div><b>When exposed</b></div><Bars data={analytics.memory_classes} empty="Device memory is not exposed by these browsers." /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>DEVICE CAPABILITY</span><h2>Logical CPU cores</h2></div><b>Browser estimate</b></div><Bars data={analytics.cpu_cores} empty="CPU concurrency is unavailable." /></article>
      <article className="qrfy-panel"><div className="qrfy-card-title"><div><span>NETWORK</span><h2>Connection quality</h2></div><b>When exposed</b></div><Bars data={analytics.connection_types} empty="Connection API is hidden or unsupported." /></article>
      <article className="qrfy-panel qr-platform-card"><div className="qrfy-card-title"><div><span>DISTRIBUTION</span><h2>Source platforms</h2></div><b>Exact + detected</b></div><Bars data={analytics.platforms} empty="No platform attribution yet." /></article>
      <article className="qrfy-panel qr-attribution-card"><div className="qrfy-card-title"><div><span>DATA QUALITY</span><h2>Source confidence</h2></div><b>{tagged.toLocaleString("en-IN")} exact</b></div><div className="qr-attribution-grid"><div className="exact"><strong>{tagged.toLocaleString("en-IN")}</strong><span>Exact</span><small>Channel-tagged QR/link</small></div><div className="detected"><strong>{detected.toLocaleString("en-IN")}</strong><span>Detected</span><small>Referrer/UA evidence</small></div><div className="unknown"><strong>{unknown.toLocaleString("en-IN")}</strong><span>Unknown</span><small>Direct QR / stripped referrer</small></div></div></article>
    </section>

    {!selected ? <section className="qrfy-panel qrfy-top-campaigns"><div className="qrfy-card-title"><div><span>PERFORMANCE</span><h2>Top QR codes</h2></div><Link href="/qr/codes">Manage all →</Link></div><div className="qrfy-campaign-list">{topCodes.map((code, index) => <button key={code.id} onClick={() => setSelected(code.id)}><span className="rank">#{index + 1}</span><div><strong>{code.name}</strong><small>{host(code.target_url)}</small></div><b>{code.total_scans.toLocaleString("en-IN")} <em>verified scans</em></b></button>)}{!topCodes.length ? <div className="qrfy-no-data">No campaigns yet.</div> : null}</div></section> : null}

    <section className="qrfy-panel qr-device-intelligence qr-device-intelligence-v23">
      <div className="qrfy-card-title qr-device-title-v23"><div><span>DEVICE INTELLIGENCE</span><h2>Repeat-device footprint</h2><p>Clean device summaries first. Technical telemetry stays available on demand instead of flooding the page.</p></div><b>{analytics.top_devices.length.toLocaleString("en-IN")} known browser/device IDs</b></div>
      <div className="qr-device-grid-v23">
        {deviceData.items.map(device=><article key={device.device_id} className="qr-device-card-v23">
          <header className="qr-device-card-head">
            <div className="qr-device-avatar"><span>{device.device_type==="Mobile"?"M":device.device_type==="Tablet"?"T":"D"}</span></div>
            <div className="qr-device-primary"><small>DEVICE {compactDeviceId(device.device_id)}</small><h3>{deviceName(device)}</h3><p>{cleanBrowserVersion(device.browser_version,device.browser)}</p></div>
            <div className="qr-device-scan-count"><strong>{device.scans.toLocaleString("en-IN")}</strong><span>verified scans</span></div>
          </header>
          <div className="qr-device-summary-v23">
            <div><span>Identity</span><strong>{device.scanner_email||"Anonymous"}</strong></div>
            <div><span>QR codes</span><strong>{device.qr_codes.toLocaleString("en-IN")}</strong></div>
            <div><span>Countries</span><strong>{device.countries.toLocaleString("en-IN")}</strong></div>
            <div><span>Last seen</span><strong>{indiaTime(device.last_seen)}</strong></div>
          </div>
          <div className="qr-device-glance">
            <span>{device.operating_system||"OS unavailable"}</span>
            {device.screen_resolution?<span>{cleanResolution(device.screen_resolution)}</span>:null}
            {device.timezone?<span>{cleanTimezone(device.timezone)}</span>:null}
            {device.language?<span>{device.language}</span>:null}
          </div>
          <details className="qr-device-details-v23">
            <summary><span>Technical details</span><b>View</b></summary>
            <div className="qr-device-detail-groups">
              <section><h4>Browser & platform</h4><dl>
                <div><dt>Browser</dt><dd>{cleanBrowserVersion(device.browser_version,device.browser)}</dd></div>
                <div><dt>OS</dt><dd>{detailText(device.operating_system)}</dd></div>
                <div><dt>Platform</dt><dd>{detailText(device.client_platform)}</dd></div>
                <div><dt>Platform version</dt><dd>{detailText(device.platform_version)}</dd></div>
                <div><dt>Vendor</dt><dd>{detailText(device.browser_vendor)}</dd></div>
              </dl></section>
              <section><h4>Hardware</h4><dl>
                <div><dt>Model</dt><dd>{detailText(device.device_model)}</dd></div>
                <div><dt>CPU</dt><dd>{device.architecture?`${device.architecture}${device.bitness?` · ${device.bitness}-bit`:""}`:"Unavailable"}</dd></div>
                <div><dt>Memory</dt><dd>{device.device_memory_gb?`${device.device_memory_gb} GB`:"Unavailable"}</dd></div>
                <div><dt>Logical cores</dt><dd>{detailText(device.hardware_concurrency)}</dd></div>
                <div><dt>Form factor</dt><dd>{detailText(device.form_factors)}</dd></div>
              </dl></section>
              <section><h4>Display & input</h4><dl>
                <div><dt>Screen</dt><dd>{detailText(cleanResolution(device.screen_resolution))}</dd></div>
                <div><dt>Viewport</dt><dd>{device.viewport_width&&device.viewport_height?`${device.viewport_width} x ${device.viewport_height}`:detailText(device.viewport)}</dd></div>
                <div><dt>Pixel ratio</dt><dd>{device.pixel_ratio?`${device.pixel_ratio}x`:"Unavailable"}</dd></div>
                <div><dt>Color depth</dt><dd>{device.color_depth?`${device.color_depth}-bit`:"Unavailable"}</dd></div>
                <div><dt>Orientation</dt><dd>{detailText(device.screen_orientation)}</dd></div>
                <div><dt>Touch</dt><dd>{device.max_touch_points!==null?`${device.max_touch_points} points`:"Unavailable"}</dd></div>
                <div><dt>Input</dt><dd>{detailText(device.input_capability)}</dd></div>
              </dl></section>
              <section><h4>Network & locale</h4><dl>
                <div><dt>Connection</dt><dd>{detailText(device.connection)}</dd></div>
                <div><dt>Quality</dt><dd>{detailText(device.network_quality)}</dd></div>
                <div><dt>Timezone</dt><dd>{detailText(cleanTimezone(device.timezone))}</dd></div>
                <div><dt>Languages</dt><dd>{detailText(device.languages||device.language)}</dd></div>
                <div><dt>Cookies</dt><dd>{boolText(device.cookies_enabled)}</dd></div>
                <div><dt>Standalone/PWA</dt><dd>{boolText(device.standalone)}</dd></div>
                <div><dt>Color gamut</dt><dd>{detailText(device.color_gamut)}</dd></div>
              </dl></section>
            </div>
          </details>
          <footer><span>First seen {indiaTime(device.first_seen)}</span><span>Last seen {indiaTime(device.last_seen)}</span></footer>
        </article>)}
        {!analytics.top_devices.length?<div className="qrfy-no-data">No verified device history yet.</div>:null}
      </div>
      <PaginationControls page={deviceData.page} pages={deviceData.pages} total={deviceData.total} start={deviceData.start} end={deviceData.end} onPageChange={setDevicePage} label="devices" />
    </section>

    <section className="qrfy-panel qrfy-recent qr-recent-v20">
      <div className="qrfy-card-title"><div><span>LIVE VERIFIED HISTORY</span><h2>Recent scans</h2></div><b>Newest first · India time</b></div>
      <div className="qrfy-table-wrap qr-recent-desktop"><table className="qrfy-scans-table"><thead><tr><th>QR code</th><th>Date & time</th><th>Country</th><th>Device / OS</th><th>Device ID / Email</th><th>Browser</th><th>Source</th><th>Confidence</th></tr></thead><tbody>{recentData.items.map(scan => <tr key={scan.id}><td><strong>{scan.qr_name}</strong></td><td>{indiaTime(scan.scanned_at)}</td><td>{countryName(scan.country)}</td><td><span className="qrfy-device">{scan.device_type}</span><small className="qr-os-sub">{scan.operating_system}{scan.device_model ? ` · ${scan.device_model}` : ""}</small></td><td><strong>{scan.device_id}</strong>{scan.scanner_email ? <small className="qr-os-sub">{scan.scanner_email}</small> : <small className="qr-os-sub">Anonymous</small>}{scan.client_platform||scan.screen_resolution||scan.timezone?<small className="qr-os-sub">{[scan.client_platform,scan.screen_resolution,scan.timezone].filter(Boolean).join(" · ")}</small>:null}
        {scan.hardware_concurrency||scan.device_memory_gb||scan.connection?<small className="qr-os-sub">{[scan.device_memory_gb?`${scan.device_memory_gb} GB RAM`:"",scan.hardware_concurrency?`${scan.hardware_concurrency} cores`:"",scan.connection,scan.network_quality].filter(Boolean).join(" · ")}</small>:null}</td><td>{scan.browser}{scan.browser_version?<small className="qr-os-sub">{cleanBrowserVersion(scan.browser_version,scan.browser)}</small>:null}</td><td><strong>{scan.platform}</strong>{scan.referrer_host ? <small className="qr-os-sub">{scan.referrer_host}</small> : null}</td><td><span className={`qr-confidence ${scan.source_confidence}`}>{confidenceLabel(scan.source_confidence)}</span></td></tr>)}{!analytics.recent_scans.length ? <tr><td colSpan={8}><div className="qrfy-no-data">No verified scan history in this scope yet.</div></td></tr> : null}</tbody></table></div>
      <div className="qr-recent-mobile">{recentData.items.map(scan => <article key={scan.id}><div><strong>{scan.qr_name}</strong><span className={`qr-confidence ${scan.source_confidence}`}>{confidenceLabel(scan.source_confidence)}</span></div><time>{indiaTime(scan.scanned_at)}</time><dl><div><dt>Country</dt><dd>{countryName(scan.country)}</dd></div><div><dt>Device</dt><dd>{scan.device_type} · {scan.operating_system}</dd></div><div><dt>Browser</dt><dd>{scan.browser}</dd></div><div><dt>Identity</dt><dd>{scan.scanner_email || scan.device_id}</dd></div><div><dt>Screen / zone</dt><dd>{[cleanResolution(scan.screen_resolution),(scan.viewport_width&&scan.viewport_height)?`viewport ${scan.viewport_width} x ${scan.viewport_height}`:(scan.viewport?`viewport ${cleanResolution(scan.viewport)}`:""),cleanTimezone(scan.timezone)].filter(Boolean).join(" · ")||"Unavailable"}</dd></div>
        <div><dt>Device capability</dt><dd>{[scan.device_memory_gb?`${scan.device_memory_gb} GB RAM`:"",scan.hardware_concurrency?`${scan.hardware_concurrency} cores`:"",scan.connection,scan.network_quality,scan.input_capability,scan.color_gamut].filter(Boolean).join(" · ")||"Browser did not expose it"}</dd></div>
        <div><dt>Source</dt><dd>{scan.platform}</dd></div></dl></article>)}{!analytics.recent_scans.length ? <div className="qrfy-no-data">No verified scans yet.</div> : null}</div>
      <PaginationControls page={recentData.page} pages={recentData.pages} total={recentData.total} start={recentData.start} end={recentData.end} onPageChange={setRecentPage} label="verified scans" />
    </section>

    <section className="qr-accuracy-note"><strong>What Anonymous Device Intelligence means</strong><p><b>Unique browsers/devices</b> uses a durable first-party anonymous identifier; one person using two browsers/devices can appear twice, and clearing browser storage can create a new identifier. Anonymous mode also records the maximum standard browser signals available—device class, OS/browser, model when exposed, platform version, architecture/bitness, approximate RAM, logical CPU concurrency, touch capability, screen/viewport, pixel ratio, timezone/language and connection quality. Unsupported or privacy-restricted fields stay “Unavailable” rather than being guessed. <b>Identify with email</b> records only the email deliberately submitted by the scanner; Gmail and MAC addresses are never silently extracted. <b>Source platform</b> is exact when you distribute a channel-tagged QR; otherwise it is detected from available signals or shown as Direct/Unknown.</p></section>

    {loading ? <div className="qrfy-loading-float">Refreshing verified statistics…</div> : null}
  </main>;
}
