"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, MouseEvent, ReactNode } from "react";
import { QrProductNav } from "../../../components/qr-product-nav";
import "./insights.css";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Period = "7d" | "30d" | "90d" | "365d" | "all";
type How = "tagged" | "detected" | "not_reported";
type Count = { label: string; scans: number };
type Source = { channel: string; label: string; group: string; how: How; scans: number; share: number; hosts: Array<{ host: string; scans: number }> };
type Overview = {
  period: Period; qr_id: string | null; qr_name: string | null; generated_at: string;
  totals: {
    scans: number; unique_devices: number; returning_devices: number; returning_share: number; scans_per_device: number;
    today: number; yesterday: number; previous_period_scans: number | null; change_pct: number | null;
    active_days: number; peak_day: string | null; peak_day_scans: number;
  };
  trend: Array<{ day: string; scans: number; unique: number }>;
  hours: number[]; weekdays: number[];
  sources: Source[];
  source_quality: { tagged: number; detected: number; not_reported: number; known_share: number };
  countries: Array<{ code: string; scans: number; share: number }>;
  states: Array<{ state: string; country: string; scans: number; share: number }>;
  cities: Array<{ city: string; state: string; country: string; scans: number }>;
  networks: Count[]; devices: Count[]; operating_systems: Count[]; browsers: Count[]; languages: Count[];
  top_qr_codes: Array<{ id: string; name: string; scans: number }>;
  accuracy: { location_coverage: number; location: string; devices: string; sources: string; verified: string };
};
type RecentScan = {
  id: number; qr_id: string; qr_name: string; scanned_at: string; country: string; device_type: string; browser: string;
  operating_system: string; device_id: string; scanner_email: string;
  source?: { label: string; how: How }; region?: string; city?: string; network?: string; platform: string;
};
type RecentResponse = { items: RecentScan[]; next_cursor: number | null; has_more: boolean };
type QrLookup = { id: string; name: string; total_scans: number };
type Place = { country: string; state: string; city: string; scans: number; devices: number; share: number; network: string; last_scan: string };
type LocationsResponse = { total_scans: number; items: Place[] };

const PERIODS: Array<[Period, string]> = [["7d", "7 days"], ["30d", "30 days"], ["90d", "90 days"], ["365d", "1 year"], ["all", "All time"]];
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOW_LABEL: Record<How, string> = { tagged: "Tagged link", detected: "Detected", not_reported: "Not reported" };
const LANGUAGE_NAMES: Record<string, string> = { en: "English", hi: "Hindi", bn: "Bengali", mr: "Marathi", te: "Telugu", ta: "Tamil", gu: "Gujarati", kn: "Kannada", ml: "Malayalam", pa: "Punjabi", or: "Odia", ur: "Urdu" };

const nf = new Intl.NumberFormat("en-IN");
function num(value: number | null | undefined): string { return nf.format(value ?? 0); }
function countryName(code: string): string {
  if (!code || code === "Unknown") return "Not reported";
  if (code.length !== 2) return code;
  try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code.toUpperCase()) ?? code; } catch { return code; }
}
function flag(code: string): string {
  if (!/^[A-Za-z]{2}$/.test(code)) return "🌐";
  return String.fromCodePoint(...code.toUpperCase().split("").map((c) => 127397 + c.charCodeAt(0)));
}
function dayLabel(iso: string, long = false): string {
  const d = new Date(`${iso}T00:00:00+05:30`);
  if (Number.isNaN(d.valueOf())) return iso;
  return new Intl.DateTimeFormat("en-IN", long ? { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" } : { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).format(d);
}
function timeLabel(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.valueOf())) return value;
  return new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(d);
}
function hourLabel(hour: number): string { return `${hour % 12 === 0 ? 12 : hour % 12}${hour < 12 ? "am" : "pm"}`; }
function pct(part: number, total: number): string { return total ? `${((part * 100) / total).toFixed(part * 100 / total < 10 ? 1 : 0)}%` : "0%"; }

function Kpi({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: "up" | "down" | "flat" }) {
  return <article className="qi-kpi"><span>{label}</span><strong>{value}</strong>{note ? <small className={tone ? `qi-${tone}` : undefined}>{note}</small> : null}</article>;
}

function BarList({ rows, total, empty = "No data in this period." }: { rows: Array<{ key: string; label: string; scans: number; hint?: string; prefix?: string }>; total: number; empty?: string }) {
  const max = Math.max(1, ...rows.map((row) => row.scans));
  if (!rows.length) return <p className="qi-empty">{empty}</p>;
  return <ul className="qi-bars">{rows.map((row) => <li key={row.key}>
    <div className="qi-bar-head"><span className="qi-bar-label">{row.prefix ? <i aria-hidden="true">{row.prefix}</i> : null}{row.label}{row.hint ? <em>{row.hint}</em> : null}</span><span className="qi-bar-value">{num(row.scans)} <small>{pct(row.scans, total)}</small></span></div>
    <div className="qi-bar-track"><b style={{ width: `${Math.max(1.5, (row.scans / max) * 100)}%` }} /></div>
  </li>)}</ul>;
}

function TrendChart({ rows }: { rows: Overview["trend"] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (!rows.length) return <p className="qi-empty">No verified scans in this period.</p>;
  const width = 1000; const height = 260; const padX = 8; const padTop = 16; const padBottom = 28;
  const max = Math.max(1, ...rows.map((r) => r.scans));
  const step = rows.length > 1 ? (width - padX * 2) / (rows.length - 1) : 0;
  const x = (i: number) => padX + i * step;
  const y = (v: number) => padTop + (height - padTop - padBottom) * (1 - v / max);
  const line = (key: "scans" | "unique") => rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r[key]).toFixed(1)}`).join(" ");
  const area = `${line("scans")} L${x(rows.length - 1).toFixed(1)},${height - padBottom} L${x(0).toFixed(1)},${height - padBottom} Z`;
  const ticks = [0, 0.5, 1].map((t) => Math.round(max * t));
  const labelEvery = Math.max(1, Math.ceil(rows.length / 8));
  const active = hover !== null ? rows[hover] : null;
  return <div className="qi-trend">
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Daily verified scans"
      onMouseLeave={() => setHover(null)}
      onMouseMove={(event: MouseEvent<SVGSVGElement>) => { const box = event.currentTarget.getBoundingClientRect(); const rel = ((event.clientX - box.left) / box.width) * width; setHover(Math.max(0, Math.min(rows.length - 1, Math.round((rel - padX) / (step || 1))))); }}>
      <defs><linearGradient id="qiArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--qi-accent)" stopOpacity="0.28" /><stop offset="100%" stopColor="var(--qi-accent)" stopOpacity="0.02" /></linearGradient></defs>
      {ticks.map((t) => <line key={t} x1={0} x2={width} y1={y(t)} y2={y(t)} className="qi-gridline" />)}
      <path d={area} fill="url(#qiArea)" />
      <path d={line("scans")} className="qi-line" />
      <path d={line("unique")} className="qi-line qi-line-2" />
      {active && hover !== null ? <g><line x1={x(hover)} x2={x(hover)} y1={padTop} y2={height - padBottom} className="qi-cursor" /><circle cx={x(hover)} cy={y(active.scans)} r={5} className="qi-dot" /></g> : null}
    </svg>
    <div className="qi-trend-axis">{rows.map((r, i) => i % labelEvery === 0 ? <span key={r.day} style={{ left: `${(x(i) / width) * 100}%` }}>{dayLabel(r.day)}</span> : null)}</div>
    <div className="qi-trend-ticks">{ticks.slice().reverse().map((t) => <span key={t}>{num(t)}</span>)}</div>
    <div className="qi-trend-legend"><span><i className="qi-swatch" />Verified scans</span><span><i className="qi-swatch qi-swatch-2" />Unique devices</span>{active ? <strong>{dayLabel(active.day, true)}: {num(active.scans)} scans · {num(active.unique)} devices</strong> : <em>Hover the chart for daily numbers</em>}</div>
  </div>;
}

function HourChart({ hours }: { hours: number[] }) {
  const max = Math.max(1, ...hours);
  const total = hours.reduce((a, b) => a + b, 0);
  const peak = hours.indexOf(Math.max(...hours));
  return <div>
    <div className="qi-hours">{hours.map((v, h) => <div key={h} title={`${hourLabel(h)}–${hourLabel((h + 1) % 24)}: ${num(v)} scans`}><b style={{ height: `${Math.max(2, (v / max) * 100)}%` }} className={h === peak ? "peak" : undefined} /><span>{h % 3 === 0 ? hourLabel(h) : ""}</span></div>)}</div>
    {total ? <p className="qi-caption">Busiest hour: <strong>{hourLabel(peak)}–{hourLabel((peak + 1) % 24)}</strong> (India time) · {pct(hours[peak] ?? 0, total)} of scans</p> : null}
  </div>;
}

function WeekChart({ days }: { days: number[] }) {
  const max = Math.max(1, ...days);
  return <div className="qi-week">{days.map((v, i) => <div key={WEEKDAYS[i]}><span>{WEEKDAYS[i]}</span><i><b style={{ width: `${(v / max) * 100}%` }} /></i><em>{num(v)}</em></div>)}</div>;
}

function LocationDetails({ period, qrId }: { period: Period; qrId: string }) {
  const [items, setItems] = useState<Place[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<"city" | "state">("city");
  const [limit, setLimit] = useState(25);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setLimit(25);
    const p = new URLSearchParams({ period }); if (qrId) p.set("qr_id", qrId);
    fetch(`${PUBLIC_API_URL}/api/v1/qr-insights/locations?${p.toString()}`, { cache: "no-store" })
      .then((r) => r.ok ? r.json() as Promise<LocationsResponse> : Promise.reject(new Error("load")))
      .then((d) => { if (!cancelled) { setItems(d.items); setTotal(d.total_scans); } })
      .catch(() => { if (!cancelled) setItems([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [period, qrId]);
  const rows = useMemo(() => {
    let list: Place[] = items;
    if (group === "state") {
      const map = new Map<string, Place & { nets: Map<string, number> }>();
      for (const it of items) {
        const key = `${it.country}|${it.state}`;
        const cur = map.get(key) ?? { ...it, city: "", scans: 0, devices: 0, share: 0, nets: new Map<string, number>() };
        cur.scans += it.scans; cur.devices += it.devices; cur.share += it.share;
        cur.nets.set(it.network, (cur.nets.get(it.network) ?? 0) + it.scans);
        if (it.last_scan > cur.last_scan) cur.last_scan = it.last_scan;
        map.set(key, cur);
      }
      list = [...map.values()].map((x) => ({ ...x, share: Math.round(x.share * 10) / 10, network: [...x.nets.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "Not reported" })).sort((a, b) => b.scans - a.scans);
    }
    const q = query.trim().toLowerCase();
    return q ? list.filter((r) => `${r.city} ${r.state} ${countryName(r.country)} ${r.network}`.toLowerCase().includes(q)) : list;
  }, [items, group, query]);
  const p = new URLSearchParams({ period }); if (qrId) p.set("qr_id", qrId);
  return <section className="qi-panel qi-wide" id="locations">
    <header><div><span className="qi-kicker">Location details</span><h2>Every state and city</h2></div>
      <div className="qi-panel-aside qi-wrap">
        <div className="qi-tabs" role="tablist"><button type="button" className={group === "city" ? "active" : ""} onClick={() => setGroup("city")}>Cities</button><button type="button" className={group === "state" ? "active" : ""} onClick={() => setGroup("state")}>States</button></div>
        <input className="qi-filter" value={query} onChange={(e: ChangeEvent<HTMLInputElement>) => { setQuery(e.target.value); setLimit(25); }} placeholder="Search state, city, network…" aria-label="Search locations" />
        <a className="qi-chip" href={`${PUBLIC_API_URL}/api/v1/qr-insights/locations.csv?${p.toString()}`}>⬇ Download (Excel)</a>
      </div>
    </header>
    <p className="qi-caption qi-top-caption">{loading ? "Loading locations…" : `${num(rows.length)} ${group === "city" ? "places" : "states"} · ${num(total)} verified scans. City = the internet network's city (approximate); state is reliable.`}</p>
    <div className="qi-table-wrap"><table className="qi-table"><thead><tr><th>{group === "city" ? "City (approx.)" : "State"}</th>{group === "city" ? <th>State</th> : null}<th>Country</th><th className="num">Scans</th><th className="num">Devices</th><th className="num">Share</th><th>Main network</th><th>Last scan</th></tr></thead>
      <tbody>{rows.slice(0, limit).map((r) => <tr key={`${r.country}|${r.state}|${r.city}`}>
        <td><strong>{group === "city" ? r.city : r.state}</strong></td>{group === "city" ? <td>{r.state}</td> : null}
        <td>{flag(r.country)} {countryName(r.country)}</td><td className="num">{num(r.scans)}</td><td className="num">{num(r.devices)}</td><td className="num">{r.share}%</td><td>{r.network}</td><td>{r.last_scan ? timeLabel(r.last_scan) : "–"}</td>
      </tr>)}{!loading && !rows.length ? <tr><td colSpan={8} className="qi-empty">No locations match.</td></tr> : null}</tbody></table></div>
    {rows.length > limit ? <button type="button" className="qi-more" onClick={() => setLimit((l) => l + 50)}>Show more ({num(rows.length - limit)} left)</button> : null}
  </section>;
}

function Panel({ kicker, title, aside, children, className }: { kicker?: string; title: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`qi-panel ${className ?? ""}`}><header><div>{kicker ? <span className="qi-kicker">{kicker}</span> : null}<h2>{title}</h2></div>{aside ? <div className="qi-panel-aside">{aside}</div> : null}</header>{children}</section>;
}

export default function QrInsightsPage() {
  const [period, setPeriod] = useState<Period>("30d");
  const [qrId, setQrId] = useState("");
  const [data, setData] = useState<Overview | null>(null);
  const [recent, setRecent] = useState<RecentResponse>({ items: [], next_cursor: null, has_more: false });
  const [cursorStack, setCursorStack] = useState<Array<number | null>>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<QrLookup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [geoView, setGeoView] = useState<"states" | "cities" | "countries" | "networks">("states");

  useEffect(() => { const id = new URLSearchParams(window.location.search).get("qr_id") ?? ""; setQrId(id); }, []);
  useEffect(() => { setCursor(null); setCursorStack([]); }, [period, qrId]);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const p = new URLSearchParams({ period }); if (qrId) p.set("qr_id", qrId);
      const r = await fetch(`${PUBLIC_API_URL}/api/v1/qr-insights/overview?${p.toString()}`, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status === 404 ? "This QR code was not found." : "Could not load QR analytics. Please try again.");
      setData(await r.json() as Overview);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load QR analytics."); } finally { setLoading(false); }
  }, [period, qrId]);
  useEffect(() => { void load(); }, [load]);

  const loadRecent = useCallback(async () => {
    try {
      const p = new URLSearchParams({ limit: "25" }); if (qrId) p.set("qr_id", qrId); if (cursor) p.set("cursor", String(cursor));
      const r = await fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/recent-scans?${p.toString()}`, { cache: "no-store" });
      if (r.ok) setRecent(await r.json() as RecentResponse);
    } catch { /* recent list is optional */ }
  }, [qrId, cursor]);
  useEffect(() => { void loadRecent(); }, [loadRecent]);

  useEffect(() => {
    if (!search.trim()) { setResults([]); return; }
    const timer = window.setTimeout(async () => {
      try {
        const p = new URLSearchParams({ limit: "10", q: search.trim(), active: "all", qr_type: "all", sort: "recent" });
        const r = await fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/codes?${p.toString()}`, { cache: "no-store" });
        if (r.ok) setResults(((await r.json()) as { items: QrLookup[] }).items);
      } catch { /* ignore */ }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  function chooseQr(id: string) { setQrId(id); setSearch(""); setResults([]); window.history.replaceState(null, "", id ? `/qr/stats?qr_id=${encodeURIComponent(id)}` : "/qr/stats"); window.scrollTo({ top: 0, behavior: "smooth" }); }

  const t = data?.totals;
  const total = t?.scans ?? 0;
  const change = t?.change_pct;
  const sourceRows = useMemo(() => (data?.sources ?? []).slice(0, 10).map((s) => ({ key: s.channel, label: s.label, scans: s.scans, hint: HOW_LABEL[s.how] })), [data]);
  const geoRows = useMemo(() => {
    if (!data) return [];
    if (geoView === "countries") return data.countries.slice(0, 12).map((c) => ({ key: c.code, label: countryName(c.code), scans: c.scans, prefix: flag(c.code) }));
    if (geoView === "cities") return data.cities.slice(0, 12).map((c) => ({ key: `${c.city}|${c.state}|${c.country}`, label: c.city, hint: [c.state, c.country === "IN" ? "" : countryName(c.country)].filter(Boolean).join(", "), scans: c.scans }));
    if (geoView === "networks") return data.networks.slice(0, 12).map((n) => ({ key: n.label, label: n.label, scans: n.scans }));
    return data.states.slice(0, 12).map((s) => ({ key: `${s.state}|${s.country}`, label: s.state, hint: s.country === "IN" ? "" : countryName(s.country), scans: s.scans }));
  }, [data, geoView]);
  const quality = data?.source_quality;
  const downloadQuery = (() => { const p = new URLSearchParams({ period }); if (qrId) p.set("qr_id", qrId); return p.toString(); })();

  return <main className="qrfy-page qi-page">
    <QrProductNav />

    <header className="qi-hero">
      <div className="qi-hero-text">
        <span className="qi-kicker">Verified scan analytics</span>
        <h1>{data?.qr_name ? data.qr_name : "QR Analytics"}</h1>
        <p>{data?.qr_name ? "Analytics for this QR code only." : "All your QR codes together."} Only real scans are counted: the scan page opened on a phone or computer. Bots and link previews are excluded.</p>
      </div>
      <div className="qi-hero-tools">
        <div className="qi-search">
          <input value={search} onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)} placeholder={qrId ? "Search another QR…" : "Search a QR code to analyse…"} aria-label="Search QR code" />
          {results.length ? <div className="qi-search-results">{results.map((row) => <button key={row.id} type="button" onClick={() => chooseQr(row.id)}><strong>{row.name}</strong><span>{num(row.total_scans)} scans</span></button>)}</div> : null}
        </div>
        {qrId ? <button type="button" className="qi-chip" onClick={() => chooseQr("")}>← All QR codes</button> : null}
        <Link className="qi-chip qi-chip-primary" href="/qr/codes">My QR codes</Link>
      </div>
    </header>

    <nav className="qi-periods" aria-label="Time period">{PERIODS.map(([value, label]) => <button key={value} type="button" className={period === value ? "active" : ""} onClick={() => setPeriod(value)}>{label}</button>)}<span className="qi-updated">{data ? `Updated ${timeLabel(data.generated_at)} · India time` : ""}</span>
      <div className="qi-downloads" aria-label="Downloads">
        <a href={`${PUBLIC_API_URL}/api/v1/qr-insights/scans.csv?${downloadQuery}`}>⬇ All scans (Excel)</a>
        <a href={`${PUBLIC_API_URL}/api/v1/qr-insights/locations.csv?${downloadQuery}`}>⬇ Locations (Excel)</a>
        <a href={`${PUBLIC_API_URL}/api/v1/qr-reports/export.pdf?${downloadQuery}`}>⬇ PDF report</a>
      </div></nav>

    {error ? <div className="qi-error" role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></div> : null}

    <section className="qi-kpis">
      <Kpi label="Verified scans" value={num(total)} note={change === null || change === undefined ? (period === "all" ? "All time" : "No earlier data to compare") : `${change > 0 ? "▲" : change < 0 ? "▼" : "■"} ${Math.abs(change)}% vs previous ${PERIODS.find(([p]) => p === period)?.[1] ?? ""}`} tone={change === null || change === undefined ? undefined : change > 0 ? "up" : change < 0 ? "down" : "flat"} />
      <Kpi label="Unique devices" value={num(t?.unique_devices)} note={`${t?.scans_per_device ?? 0} scans per device`} />
      <Kpi label="Returning devices" value={`${t?.returning_share ?? 0}%`} note={`${num(t?.returning_devices)} scanned more than once`} />
      <Kpi label="Today" value={num(t?.today)} note={`Yesterday ${num(t?.yesterday)}`} />
      <Kpi label="Best day" value={t?.peak_day ? num(t.peak_day_scans) : "–"} note={t?.peak_day ? dayLabel(t.peak_day, true) : "No scans yet"} />
      <Kpi label="Source recognised" value={`${quality?.known_share ?? 0}%`} note="Rest: camera scans & apps that report nothing" />
    </section>

    <Panel kicker="Daily activity" title="Scans over time" className="qi-wide" aside={<strong className="qi-big">{num(total)}</strong>}>
      <TrendChart rows={data?.trend ?? []} />
    </Panel>

    <div className="qi-grid">
      <Panel kicker="Where scans come from" title="Sources" aside={<span className="qi-muted-small">Detected automatically</span>}>
        {quality && total ? <div className="qi-quality" title="How the source of each scan is known">
          <b className="tagged" style={{ width: `${(quality.tagged / total) * 100}%` }} />
          <b className="detected" style={{ width: `${(quality.detected / total) * 100}%` }} />
          <b className="unknown" style={{ width: `${(quality.not_reported / total) * 100}%` }} />
        </div> : null}
        {quality && total ? <div className="qi-quality-legend"><span><i className="tagged" />Tagged link {pct(quality.tagged, total)}</span><span><i className="detected" />Detected {pct(quality.detected, total)}</span><span><i className="unknown" />Not reported {pct(quality.not_reported, total)}</span></div> : null}
        <BarList rows={sourceRows} total={total} />
        <p className="qi-note">One QR link works everywhere. The source is recognised automatically when the phone or app reports it: Google Lens, WhatsApp on Android, Instagram, Facebook, YouTube, Gmail, Google Search and more. Phone-camera scans (iPhone camera, many Android cameras) and some apps report nothing, so they show as <strong>Not reported</strong>.</p>
      </Panel>

      <Panel kicker="Location" title="Where people are" aside={<div className="qi-tabs" role="tablist">{(["states", "cities", "countries", "networks"] as const).map((v) => <button key={v} type="button" role="tab" aria-selected={geoView === v} className={geoView === v ? "active" : ""} onClick={() => setGeoView(v)}>{v === "states" ? "States" : v === "cities" ? "Cities" : v === "countries" ? "Countries" : "Networks"}</button>)}</div>}>
        <BarList rows={geoRows} total={total} empty="No location reported for these scans." />
        <a className="qi-link qi-link-block" href="#locations">See every state & city, and download →</a>
        <p className="qi-note">{geoView === "cities" ? "Approximate: this is the city of the mobile or internet network. On Indian mobile data it is often the operator's hub city (e.g. Patna for much of Bihar)." : geoView === "networks" ? "Mobile operator or internet provider reported for the scan." : `From the visitor's internet network. Location reported for ${data?.accuracy.location_coverage ?? 0}% of scans in this period.`}</p>
      </Panel>

      <Panel kicker="Timing" title="When people scan">
        <HourChart hours={data?.hours ?? new Array(24).fill(0)} />
        <WeekChart days={data?.weekdays ?? new Array(7).fill(0)} />
      </Panel>

      <Panel kicker="Technology" title="Devices">
        <div className="qi-split">
          <div><h3>Device type</h3><BarList rows={(data?.devices ?? []).map((r) => ({ key: r.label, label: r.label, scans: r.scans }))} total={total} /></div>
          <div><h3>Operating system</h3><BarList rows={(data?.operating_systems ?? []).slice(0, 5).map((r) => ({ key: r.label, label: r.label, scans: r.scans }))} total={total} /></div>
          <div><h3>Browser</h3><BarList rows={(data?.browsers ?? []).slice(0, 5).map((r) => ({ key: r.label, label: r.label, scans: r.scans }))} total={total} /></div>
          <div><h3>Phone language</h3><BarList rows={(data?.languages ?? []).slice(0, 5).map((r) => ({ key: r.label, label: LANGUAGE_NAMES[r.label] ?? r.label, scans: r.scans }))} total={total} /></div>
        </div>
      </Panel>
    </div>

    <LocationDetails period={period} qrId={qrId} />

    {!qrId && data?.top_qr_codes.length ? <Panel kicker="Portfolio" title="Top QR codes" className="qi-wide">
      <ol className="qi-top">{data.top_qr_codes.map((row, i) => <li key={row.id}><button type="button" onClick={() => chooseQr(row.id)}><span className="qi-rank">{i + 1}</span><strong>{row.name}</strong><span className="qi-top-bar"><b style={{ width: `${(row.scans / Math.max(1, data.top_qr_codes[0]?.scans ?? 1)) * 100}%` }} /></span><em>{num(row.scans)}</em><small>{pct(row.scans, total)}</small></button></li>)}</ol>
    </Panel> : null}

    <Panel kicker="Live feed" title="Latest scans" className="qi-wide" aside={<div className="qi-pager"><button type="button" disabled={!cursorStack.length} onClick={() => { const s = [...cursorStack]; const prev = s.pop() ?? null; setCursorStack(s); setCursor(prev); }}>← Newer</button><button type="button" disabled={!recent.next_cursor} onClick={() => { if (!recent.next_cursor) return; setCursorStack((s) => [...s, cursor]); setCursor(recent.next_cursor); }}>Older →</button></div>}>
      <div className="qi-table-wrap"><table className="qi-table"><thead><tr><th>Time (IST)</th>{qrId ? null : <th>QR code</th>}<th>Location (approx.)</th><th>Source</th><th>Device</th><th>Network</th></tr></thead>
        <tbody>{recent.items.map((s) => <tr key={s.id}>
          <td>{timeLabel(s.scanned_at)}</td>
          {qrId ? null : <td><button type="button" className="qi-cell-link" onClick={() => chooseQr(s.qr_id)}>{s.qr_name}</button></td>}
          <td>{flag(s.country)} {[s.city, s.region].filter(Boolean).join(", ") || countryName(s.country)}</td>
          <td>{s.source ? <><span>{s.source.label}</span> <span className={`qi-badge ${s.source.how}`}>{HOW_LABEL[s.source.how]}</span></> : s.platform}</td>
          <td>{s.device_type} · {s.operating_system}<small>{s.browser} · {s.device_id}</small></td>
          <td>{s.network ?? "–"}</td>
        </tr>)}{!recent.items.length ? <tr><td colSpan={6} className="qi-empty">No scans yet.</td></tr> : null}</tbody></table></div>
    </Panel>

    <section className="qi-accuracy"><h2>How to read these numbers</h2><dl>
      <div><dt>Verified scans</dt><dd>{data?.accuracy.verified ?? "Only real scans are counted."}</dd></div>
      <div><dt>Location</dt><dd>{data?.accuracy.location ?? ""}</dd></div>
      <div><dt>Sources</dt><dd>{data?.accuracy.sources ?? ""}</dd></div>
      <div><dt>Unique devices</dt><dd>{data?.accuracy.devices ?? ""}</dd></div>
    </dl><p>Detailed city, device and export tables: <Link href="/qr/reports">Geo & Device reports</Link>.</p></section>

    {loading ? <div className="qi-loading" role="status">Updating…</div> : null}
  </main>;
}
