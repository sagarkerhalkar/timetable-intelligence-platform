"use client";

import {useCallback, useEffect, useMemo, useState} from "react";
import {QrProductNav} from "../../../components/qr-product-nav";
import "./reports.css";

type Period = "7d" | "30d" | "90d" | "365d" | "all";
type View = "locations" | "devices";
type DeviceView = "visitors" | "categories";
type GeoRow = {country: string; state_region: string; city: string; scans: number; estimated_devices: number};
type DeviceRow = {qr_id: string; qr_name: string; qr_slug: string; device_id: string; scans: number; first_seen_utc: string; last_seen_utc: string; device_type: string; operating_system: string; browser: string};
type TypeRow = {device_type: string; operating_system: string; browser: string; scans: number; estimated_devices: number};
type Report = {period: Period; qr_id: string | null; verified_scans: number; estimated_unique_devices: number; locations: GeoRow[]; devices: DeviceRow[]; device_types: TypeRow[]; accuracy: {devices: string; location: string}};
type QrItem = {id: string; name: string; slug: string};

const API = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const PAGE_SIZE = 12;
const fmt = (n: number) => n.toLocaleString("en-IN");
const clean = (value?: string | null) => !value || value.trim().toLowerCase() === "unknown" ? "" : value.trim();
const periods: {id: Period; label: string}[] = [
  {id: "7d", label: "7D"}, {id: "30d", label: "30D"}, {id: "90d", label: "90D"},
  {id: "365d", label: "1Y"}, {id: "all", label: "All"},
];
function countryName(value: string): string {
  if (!clean(value)) return "Unknown";
  try {return new Intl.DisplayNames(["en"], {type: "region"}).of(value) || value;}
  catch {return value;}
}
function timeLabel(value: string): string {
  if (!value) return "—";
  const parsed = new Date(value.endsWith("Z") || value.includes("+") ? value : value.replace(" ", "T") + "Z");
  return Number.isNaN(parsed.valueOf()) ? value.slice(0, 16) : parsed.toLocaleDateString("en-IN", {day: "2-digit", month: "short", year: "2-digit"});
}
function Paging({page, pages, total, onPage}: {page: number; pages: number; total: number; onPage: (n: number) => void}) {
  return <div className="qrg-paging"><span>{fmt(total)} {total === 1 ? "result" : "results"} · Page {page} / {pages}</span><div>
    <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Previous</button>
    <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next →</button>
  </div></div>;
}

export default function QrGeoDeviceReports() {
  const [view, setView] = useState<View>("locations");
  const [deviceView, setDeviceView] = useState<DeviceView>("visitors");
  const [period, setPeriod] = useState<Period>("30d");
  const [qrId, setQrId] = useState("");
  const [qrSearch, setQrSearch] = useState("");
  const [qrResults, setQrResults] = useState<QrItem[]>([]);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("qr_id") || "";
    if (id) setQrId(id);
    if (params.get("tab") === "devices") setView("devices");
    // Old bookmarked store tab is intentionally redirected to location reporting.
    if (params.get("tab") === "stores") window.history.replaceState(null, "", "/qr/reports?tab=locations");
  }, []);
  const reportQuery = useMemo(() => {
    const params = new URLSearchParams({period});
    if (qrId) params.set("qr_id", qrId);
    return params.toString();
  }, [period, qrId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/v1/qr-reports/summary?${reportQuery}`, {cache: "no-store"});
      if (!response.ok) throw new Error(`Geo & Devices API returned ${response.status}. Confirm the API was restarted after this update.`);
      const next = await response.json() as Report;
      if (typeof next.estimated_unique_devices !== "number") throw new Error("The old reporting API is still running. Restart the API before opening this page.");
      setReport(next);
      setUpdatedAt(new Date().toLocaleTimeString("en-IN", {hour: "2-digit", minute: "2-digit"}));
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Could not load report");
    } finally {setLoading(false);}
  }, [reportQuery]);
  useEffect(() => {void load();}, [load]);
  useEffect(() => {setFilter(""); setPage(1);}, [view, deviceView, qrId, period]);

  useEffect(() => {
    if (!qrSearch.trim()) {setQrResults([]); return;}
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const query = new URLSearchParams({q: qrSearch.trim(), limit: "10", active: "all"});
        const response = await fetch(`${API}/api/v1/qr-scale/codes?${query}`, {cache: "no-store"});
        if (response.ok && active) {
          const data = await response.json() as {items: QrItem[]};
          setQrResults(Array.isArray(data.items) ? data.items : []);
        }
      } catch {if (active) setQrResults([]);}
    }, 250);
    return () => {active = false; window.clearTimeout(timer);};
  }, [qrSearch]);

  function setSelection(id: string, label = "") {
    setQrId(id); setQrSearch(label); setQrResults([]);
    const params = new URLSearchParams({tab: view});
    if (id) params.set("qr_id", id);
    window.history.replaceState(null, "", `/qr/reports?${params}`);
  }
  function changeView(next: View) {
    setView(next);
    const params = new URLSearchParams({tab: next});
    if (qrId) params.set("qr_id", qrId);
    window.history.replaceState(null, "", `/qr/reports?${params}`);
  }
  const download = (section: "locations" | "devices" | "types") => `${API}/api/v1/qr-reports/export.csv?${reportQuery}&section=${section}`;
  const exportPDF = `${API}/api/v1/qr-reports/export.pdf?${reportQuery}`;
  const query = filter.trim().toLocaleLowerCase();
  const locations = useMemo(() => (report?.locations || []).filter(x => !query || [countryName(x.country), x.state_region, x.city].some(v => v.toLocaleLowerCase().includes(query))), [report, query]);
  const individual = useMemo(() => (report?.devices || []).filter(x => !query || [x.qr_name, x.device_id, x.device_type, x.operating_system, x.browser].some(v => v.toLocaleLowerCase().includes(query))), [report, query]);
  const types = useMemo(() => (report?.device_types || []).filter(x => !query || [x.device_type, x.operating_system, x.browser].some(v => v.toLocaleLowerCase().includes(query))), [report, query]);
  const activeRows = view === "locations" ? locations.length : deviceView === "visitors" ? individual.length : types.length;
  const pages = Math.max(1, Math.ceil(activeRows / PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const paginate = <T,>(rows: T[]) => rows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const countries = new Set((report?.locations || []).map(x => x.country).filter(x => clean(x))).size;
  const activeCSV = view === "locations" ? "locations" : deviceView === "visitors" ? "devices" : "types";

  return <main className="qrg-page">
    <QrProductNav />
    <section className="qrg-topline"><div className="qrg-title-group"><div className="qrg-mark">◎</div><div>
      <span className="qrg-eyebrow">NEXTTOPPERS / QR INTELLIGENCE</span>
      <h1>Geo & Device <span>Analytics</span></h1>
      <p>Where QR scans happen, estimated unique devices and repeat scans.</p>
    </div></div><div className="qrg-top-actions"><span className="qrg-refreshed">{updatedAt ? `Updated ${updatedAt}` : "Read-only reporting"}</span>
      <button type="button" className="qrg-soft-button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "↻ Refresh"}</button>
      <a className="qrg-primary-button" href={exportPDF} download>↓ PDF report</a>
    </div></section>
    <section className="qrg-toolbar" aria-label="Report filters"><div className="qrg-period" aria-label="Time range">{periods.map(p => <button key={p.id} type="button" className={period === p.id ? "active" : ""} aria-pressed={period === p.id} onClick={() => setPeriod(p.id)}>{p.label}</button>)}</div>
      <div className="qrg-qrselect"><label htmlFor="qrg-search">QR FILTER</label><input id="qrg-search" value={qrSearch} onChange={e => setQrSearch(e.target.value)} placeholder="All QR codes · Search by name" autoComplete="off" />
        {qrResults.length > 0 && <div className="qrg-results">{qrResults.map(item => <button type="button" key={item.id} onClick={() => setSelection(item.id, `${item.name} (${item.slug})`)}><b>{item.name}</b><small>/{item.slug}</small></button>)}</div>}</div>
      {qrId && <button type="button" className="qrg-clear" onClick={() => setSelection("")}>× All codes</button>}
    </section>
    {error && <div className="qrg-error" role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></div>}
    <section className="qrg-stats" aria-label="Key statistics">
      <article><span>VERIFIED SCANS</span><strong>{report ? fmt(report.verified_scans) : "—"}</strong><small>Confirmed QR visits</small><i className="qrg-stat-icon">↗</i></article>
      <article><span>ESTIMATED UNIQUE DEVICES</span><strong>{report ? fmt(report.estimated_unique_devices) : "—"}</strong><small>Distinct browser profiles · not hardware IDs</small><i className="qrg-stat-icon">▣</i></article>
      <article><span>COUNTRIES</span><strong>{report ? fmt(countries) : "—"}</strong><small>With recorded location</small><i className="qrg-stat-icon">◎</i></article>
    </section>
    <section className="qrg-workspace"><div className="qrg-view-tabs" role="tablist" aria-label="Analytics sections">
      <button id="qrg-tab-locations" role="tab" type="button" aria-selected={view === "locations"} aria-controls="qrg-panel-locations" className={view === "locations" ? "active" : ""} onClick={() => changeView("locations")}><span className="qrg-tab-icon">◎</span><span><b>Locations</b><small>Country · State · City</small></span></button>
      <button id="qrg-tab-devices" role="tab" type="button" aria-selected={view === "devices"} aria-controls="qrg-panel-devices" className={view === "devices" ? "active" : ""} onClick={() => changeView("devices")}><span className="qrg-tab-icon">▣</span><span><b>Devices</b><small>Estimated devices · repeat scans</small></span></button>
    </div>
      <div className="qrg-panel" id={`qrg-panel-${view}`} role="tabpanel" aria-labelledby={`qrg-tab-${view}`}>
        <div className="qrg-panel-head"><div><h2>{view === "locations" ? "Location intelligence" : "Device intelligence"}</h2>
          <p>{view === "locations" ? "Country, state and city; count each visitor ID once per location." : "Count scans by anonymous device profile and by device category."}</p></div>
          <div className="qrg-table-actions"><input type="search" value={filter} onChange={e => {setFilter(e.target.value); setPage(1);}} aria-label="Search current table" placeholder="Search these results…" />
            <a className="qrg-export" href={download(activeCSV)}>↓ Export CSV</a></div></div>
        {view === "devices" && <div className="qrg-subtabs" role="group" aria-label="Device display">
          <button className={deviceView === "visitors" ? "active" : ""} type="button" onClick={() => setDeviceView("visitors")}>Individual devices (estimated)</button>
          <button className={deviceView === "categories" ? "active" : ""} type="button" onClick={() => setDeviceView("categories")}>Device categories</button>
        </div>}
        {view === "locations" && <><div className="qrg-table-scroll"><table><thead><tr><th>Country</th><th>State / Region</th><th>City</th><th className="qrg-num">Scans</th><th className="qrg-num">Estimated devices</th></tr></thead><tbody>
          {paginate(locations).map((x, i) => <tr key={`${x.country}-${x.state_region}-${x.city}-${i}`}><td><span className="qrg-country-dot">◎</span>{countryName(x.country)}</td><td>{clean(x.state_region) || <span className="qrg-muted">Unknown</span>}</td><td>{clean(x.city) || <span className="qrg-muted">Unknown</span>}</td><td className="qrg-num"><b>{fmt(x.scans)}</b></td><td className="qrg-num">{fmt(x.estimated_devices)}</td></tr>)}
          {locations.length === 0 && <tr><td colSpan={5} className="qrg-empty">No location records in this selection</td></tr>}
        </tbody></table></div><Paging page={currentPage} pages={pages} total={activeRows} onPage={setPage}/></>}
        {view === "devices" && deviceView === "visitors" && <><div className="qrg-table-scroll"><table><thead><tr><th>QR code</th><th>Device ID (anonymous)</th><th>Device category</th><th>Browser</th><th className="qrg-num">Scans</th><th>Last seen</th></tr></thead><tbody>
          {paginate(individual).map((x,i) => <tr key={`${x.qr_id}-${x.device_id}-${i}`}><td className="qrg-qrname">{x.qr_name}</td><td><code className="qrg-id">{x.device_id}</code></td><td>{x.device_type} <small className="qrg-muted">· {x.operating_system}</small></td><td>{x.browser}</td><td className="qrg-num"><b>{fmt(x.scans)}</b></td><td className="qrg-nowrap">{timeLabel(x.last_seen_utc)}</td></tr>)}
          {individual.length === 0 && <tr><td colSpan={6} className="qrg-empty">No identifiable device profiles in this selection</td></tr>}
        </tbody></table></div><Paging page={currentPage} pages={pages} total={activeRows} onPage={setPage}/></>}
        {view === "devices" && deviceView === "categories" && <><div className="qrg-table-scroll"><table><thead><tr><th>Device type</th><th>Operating system</th><th>Browser</th><th className="qrg-num">Scans</th><th className="qrg-num">Estimated devices</th></tr></thead><tbody>
          {paginate(types).map((x,i) => <tr key={`${x.device_type}-${x.operating_system}-${x.browser}-${i}`}><td><b>{x.device_type}</b></td><td>{x.operating_system}</td><td>{x.browser}</td><td className="qrg-num"><b>{fmt(x.scans)}</b></td><td className="qrg-num">{fmt(x.estimated_devices)}</td></tr>)}
          {types.length === 0 && <tr><td colSpan={5} className="qrg-empty">No device data in this selection</td></tr>}
        </tbody></table></div><Paging page={currentPage} pages={pages} total={activeRows} onPage={setPage}/></>}
      </div>
    </section>
    <details className="qrg-accuracy"><summary>How accurate is the device count? <span>⌄</span></summary><p>Estimated devices count distinct anonymous IDs stored by the QR scanning browser. Repeat scans with the same ID count as one device in the selected period/location. Chrome and Safari on one phone, private browsing or cleared browser storage can create separate IDs. This is not an exact physical hardware count. Location is approximate. Device totals per location can overlap; do not sum them as a global unique total.</p></details>
  </main>;
}
