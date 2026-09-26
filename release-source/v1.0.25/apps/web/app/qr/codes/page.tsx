"use client";

import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PaginationControls } from "../../../components/pagination-controls";
import { QrProductNav } from "../../../components/qr-product-nav";
import { paginateItems } from "../../../lib/pagination";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type QrCodeRecord = {
  id: string;
  name: string;
  slug: string;
  qr_type: "url" | "calendar" | "contact" | "email" | "geo" | "phone" | "wifi";
  tracking_mode: "tracked" | "direct";
  identity_mode: "anonymous" | "email";
  target_url: string;
  content: Record<string, string | boolean | number>;
  active: boolean;
  created_at: string;
  updated_at: string;
  total_scans: number;
  unique_visitors: number;
  unique_emails: number;
  country_count: number;
  legacy_scans: number;
  template_id: string | null;
  template_name: string | null;
};

type Filter = "all" | "active" | "inactive";
type Sort = "recent" | "oldest" | "scans" | "unique";
type Channel = { value: string; label: string; icon: string; note: string };

const CHANNELS: readonly Channel[] = [
  { value: "web", label: "Web / Website", icon: "🌐", note: "Exact source tag" },
  { value: "whatsapp", label: "WhatsApp", icon: "◉", note: "Exact source tag" },
  { value: "telegram", label: "Telegram", icon: "➤", note: "Exact source tag" },
  { value: "instagram", label: "Instagram", icon: "◎", note: "Exact source tag" },
  { value: "google-chat", label: "Google Chat", icon: "◫", note: "Exact source tag" },
  { value: "facebook", label: "Facebook", icon: "f", note: "Exact source tag" },
  { value: "messenger", label: "Messenger", icon: "⚡", note: "Exact source tag" },
  { value: "linkedin", label: "LinkedIn", icon: "in", note: "Exact source tag" },
  { value: "email", label: "Email", icon: "✉", note: "Exact source tag" },
  { value: "teams", label: "Microsoft Teams", icon: "T", note: "Exact source tag" },
  { value: "slack", label: "Slack", icon: "#", note: "Exact source tag" },
  { value: "discord", label: "Discord", icon: "◌", note: "Exact source tag" }
] as const;

function host(value: string): string {
  try { return new URL(value).hostname.replace(/^www\./, ""); } catch { return value; }
}

const TYPE_LABELS: Record<QrCodeRecord["qr_type"], string> = { url: "Website", calendar: "Calendar", contact: "Contact", email: "Email", geo: "Location", phone: "Phone", wifi: "Wi‑Fi" };
function destination(code: QrCodeRecord): string {
  if (code.qr_type === "url") return host(String(code.content?.url || code.target_url));
  if (code.qr_type === "wifi") return String(code.content?.ssid || "Wi‑Fi network");
  if (code.qr_type === "calendar") return String(code.content?.title || "Calendar event");
  if (code.qr_type === "contact") return String(code.content?.full_name || "Contact");
  if (code.qr_type === "email") return String(code.content?.email || "Email");
  if (code.qr_type === "phone") return String(code.content?.phone || "Phone");
  return String(code.content?.label || "Location");
}

function sourceValue(code: QrCodeRecord): string {
  if (code.qr_type === "url") return String(code.content?.url || code.target_url || "");
  return code.target_url || destination(code);
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric"
  }).format(date);
}

function imageUrl(code: QrCodeRecord, format: "png" | "svg" | "pdf", source?: string, download = true): string {
  const params = new URLSearchParams({ format });
  if (download) params.set("download", "true");
  if (source) params.set("source", source);
  return `${PUBLIC_API_URL}/api/v1/qr-codes/${code.id}/image?${params.toString()}`;
}

function downloadFile(url: string) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

async function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(value); return; } catch { /* fallback below */ }
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

export default function QrCodesPage() {
  const [codes, setCodes] = useState<QrCodeRecord[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("recent");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [previewCode, setPreviewCode] = useState<QrCodeRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [channelCode, setChannelCode] = useState<QrCodeRecord | null>(null);
  const [channel, setChannel] = useState("whatsapp");
  const [channelFormat, setChannelFormat] = useState<"png" | "svg" | "pdf">("png");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes`, { cache: "no-store" });
      if (!response.ok) throw new Error("Could not load saved QR codes.");
      const next = await response.json() as QrCodeRecord[];
      setCodes(next);
      setSelectedIds((current) => new Set([...current].filter((id) => next.some((code) => code.id === id))));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load saved QR codes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [filter, search, sort]);

  useEffect(() => {
    function closeMenus(exceptTarget?: EventTarget | null) {
      document.querySelectorAll<HTMLDetailsElement>("details.qr-actions-details[open]").forEach((item) => {
        if (!(exceptTarget instanceof Node) || !item.contains(exceptTarget)) item.open = false;
      });
    }
    function onPointerDown(event: PointerEvent) { closeMenus(event.target); }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") { closeMenus(); setPreviewCode(null); setChannelCode(null); }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("pointerdown", onPointerDown); document.removeEventListener("keydown", onKeyDown); };
  }, []);

  function closeActionMenus() {
    document.querySelectorAll<HTMLDetailsElement>("details.qr-actions-details[open]").forEach((item) => { item.open = false; });
  }

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const rows = codes.filter((code) => {
      if (filter === "active" && !code.active) return false;
      if (filter === "inactive" && code.active) return false;
      if (!needle) return true;
      return `${code.name} ${code.qr_type} ${destination(code)} ${code.target_url}`.toLowerCase().includes(needle);
    });
    return rows.sort((a, b) => {
      if (sort === "scans") return b.total_scans - a.total_scans;
      if (sort === "unique") return b.unique_visitors - a.unique_visitors;
      if (sort === "oldest") return new Date(a.created_at).valueOf() - new Date(b.created_at).valueOf();
      return new Date(b.created_at).valueOf() - new Date(a.created_at).valueOf();
    });
  }, [codes, filter, search, sort]);

  const pageData = useMemo(() => paginateItems(filtered, page, 8), [filtered, page]);
  useEffect(() => { if (page !== pageData.page) setPage(pageData.page); }, [page, pageData.page]);

  async function setActive(code: QrCodeRecord) {
    setError(""); setMessage("");
    const response = await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${code.id}/active?active=${!code.active}`, { method: "POST" });
    if (!response.ok) { setError("Could not change QR status."); return; }
    setMessage(`${code.name} is now ${code.active ? "Inactive" : "Active"}.`);
    await load();
  }

  async function clearData(code: QrCodeRecord) {
    if (!window.confirm(`Clear verified and legacy scan history for “${code.name}”?\n\nThe QR remains saved and keeps its current Active/Inactive status.`)) return;
    const response = await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${code.id}/scans`, { method: "DELETE" });
    if (!response.ok) { setError("Could not clear scan data."); return; }
    setMessage(`Scan history cleared for ${code.name}.`);
    await load();
  }

  async function deleteCode(code: QrCodeRecord) {
    if (!window.confirm(`Permanently delete “${code.name}”?\n\nThe QR campaign and all scan history will be removed. Existing printed copies will stop working.`)) return;
    const response = await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${code.id}`, { method: "DELETE" });
    if (!response.ok) { setError("Could not delete this QR code."); return; }
    setSelectedIds((current) => { const next = new Set(current); next.delete(code.id); return next; });
    setMessage(`${code.name} was permanently deleted.`);
    await load();
  }

  async function deleteSelected() {
    const ids = [...selectedIds];
    if (!ids.length) return;
    if (!window.confirm(`Permanently delete ${ids.length} selected QR code${ids.length === 1 ? "" : "s"}?\n\nEach QR uses the existing protected delete route. Shared template/logo/background assets remain reference-safe.`)) return;
    setError(""); setMessage("");
    let deleted = 0;
    let failed = 0;
    for (let start = 0; start < ids.length; start += 5) {
      const batch = ids.slice(start, start + 5);
      const results = await Promise.all(batch.map(async (id) => {
        try { return (await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${id}`, { method: "DELETE" })).ok; } catch { return false; }
      }));
      deleted += results.filter(Boolean).length;
      failed += results.filter((ok) => !ok).length;
    }
    setSelectedIds(new Set());
    if (failed) setError(`${deleted} QR code${deleted === 1 ? "" : "s"} deleted; ${failed} could not be deleted.`);
    else setMessage(`${deleted} selected QR code${deleted === 1 ? "" : "s"} permanently deleted.`);
    await load();
  }

  function toggleSelected(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function selectThisPage() {
    setSelectedIds((current) => {
      const next = new Set(current);
      pageData.items.forEach((code) => next.add(code.id));
      return next;
    });
  }

  async function copySource(code: QrCodeRecord) {
    await copyText(sourceValue(code));
    setMessage(`Source/destination copied for ${code.name}.`);
  }

  async function copyQrLink(code: QrCodeRecord) {
    const value = code.tracking_mode === "tracked" ? new URL(`/q/${code.slug}`, window.location.origin).toString() : sourceValue(code);
    await copyText(value);
    setMessage(`${code.tracking_mode === "tracked" ? "Tracked QR link" : "Direct destination"} copied for ${code.name}.`);
  }

  function downloadChannelVariant() {
    if (!channelCode) return;
    downloadFile(imageUrl(channelCode, channelFormat, channel, true));
    const label = CHANNELS.find((item) => item.value === channel)?.label ?? channel;
    setMessage(`${label} tagged ${channelFormat.toUpperCase()} downloaded. Scans from this distributed QR can be attributed exactly to ${label}.`);
    setChannelCode(null);
  }

  return (
    <main className="qrfy-page qr-route-enter qr-library-v125">
      <QrProductNav />
      <header className="qrfy-page-header">
        <div>
          <p className="qrfy-kicker">QR management</p>
          <h1>My QR codes</h1>
          <p>Large QR cards, clean pagination and bulk management. Verified scan totals exclude preview bots and unconfirmed legacy hits.</p>
        </div>
        <Link className="qrfy-button primary" href="/qr">＋ Create New</Link>
      </header>

      {message ? <div className="qrfy-toast success">{message}</div> : null}
      {error ? <div className="qrfy-toast error">{error}</div> : null}

      <section className="qrfy-panel qrfy-library-shell">
        <div className="qrfy-library-top">
          <div className="qrfy-tabs" role="tablist" aria-label="QR status">
            <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>All <span>{codes.length}</span></button>
            <button className={filter === "active" ? "active" : ""} onClick={() => setFilter("active")}>Active <span>{codes.filter((x) => x.active).length}</span></button>
            <button className={filter === "inactive" ? "active" : ""} onClick={() => setFilter("inactive")}>Inactive <span>{codes.filter((x) => !x.active).length}</span></button>
          </div>
          <div className="qrfy-library-controls">
            <label className="qrfy-search"><span>⌕</span><input value={search} onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)} placeholder="Search name or destination…" /></label>
            <select value={sort} onChange={(e: ChangeEvent<HTMLSelectElement>) => setSort(e.target.value as Sort)} aria-label="Sort QR codes">
              <option value="recent">Sort: Most recent</option>
              <option value="oldest">Sort: Oldest</option>
              <option value="scans">Sort: Verified scans</option>
              <option value="unique">Sort: Unique devices</option>
            </select>
          </div>
        </div>

        <div className="qr-selection-bar-v125">
          <div><strong>{selectedIds.size.toLocaleString("en-IN")}</strong><span>selected across all pages</span></div>
          <div>
            <button type="button" onClick={selectThisPage} disabled={!pageData.items.length}>Select this page</button>
            <button type="button" onClick={() => setSelectedIds(new Set())} disabled={!selectedIds.size}>Clear selection</button>
            <button type="button" className="danger" onClick={() => void deleteSelected()} disabled={!selectedIds.size}>Delete Selected{selectedIds.size ? ` (${selectedIds.size})` : ""}</button>
          </div>
        </div>

        <div className="qr-card-grid-v125">
          {pageData.items.map((code) => (
            <article key={code.id} className={`qr-library-card-v125 ${selectedIds.has(code.id) ? "selected" : ""}`}>
              <div className="qr-card-select-v125">
                <label><input type="checkbox" checked={selectedIds.has(code.id)} onChange={() => toggleSelected(code.id)} /><span>Select</span></label>
                <span className={code.active ? "qrfy-state active" : "qrfy-state inactive"}>{code.active ? "Active" : "Inactive"}</span>
              </div>

              <button className="qr-card-preview-v125" type="button" onClick={() => setPreviewCode(code)} title={`Show QR for ${code.name}`}>
                <img src={imageUrl(code, "png", undefined, false)} alt={`QR code for ${code.name}`} />
                <span>Show QR</span>
              </button>

              <div className="qr-card-title-v125">
                <div><span className="qrfy-type-pill">◉ {TYPE_LABELS[code.qr_type]}</span><small>{code.tracking_mode === "tracked" ? (code.identity_mode === "email" ? "Tracked · Email ID" : "Tracked · Anonymous") : "Direct"}</small></div>
                <h2>{code.name}</h2>
                <p>{destination(code)}</p>
                {code.template_name ? <small className="qr-template-mini">Template · {code.template_name}</small> : null}
              </div>

              <div className="qr-card-metrics-v125">
                <div><span>Verified scans</span><strong>{code.total_scans.toLocaleString("en-IN")}</strong></div>
                <div><span>Unique devices</span><strong>{code.unique_visitors.toLocaleString("en-IN")}</strong></div>
                <div><span>Countries</span><strong>{code.country_count.toLocaleString("en-IN")}</strong></div>
                <div><span>Created</span><strong>{formatDate(code.created_at)}</strong></div>
              </div>

              {code.legacy_scans > 0 ? <div className="qr-mobile-legacy">{code.legacy_scans} legacy/unverified hits kept separately.</div> : null}

              <div className="qr-card-link-v125">
                <span>Source / destination</span>
                <div><code title={sourceValue(code)}>{sourceValue(code)}</code><button type="button" onClick={() => void copySource(code)}>Copy Source Link</button></div>
              </div>
              <div className="qr-card-link-v125">
                <span>{code.tracking_mode === "tracked" ? "Tracked public QR link" : "Direct QR destination"}</span>
                <div><code>{code.tracking_mode === "tracked" ? `/q/${code.slug}` : sourceValue(code)}</code><button type="button" onClick={() => void copyQrLink(code)}>Copy QR Link</button></div>
              </div>

              <div className="qr-card-primary-actions-v125">
                <Link href={`/qr/stats?qr_id=${code.id}`}>Analytics</Link>
                <Link href={`/qr?edit=${code.id}`}>Edit</Link>
                <button type="button" onClick={() => setPreviewCode(code)}>Show QR</button>
                <a href={imageUrl(code, "png")}>PNG</a>
              </div>

              <details className="qr-actions-details qr-card-more-v125">
                <summary>More actions</summary>
                <div className="qrfy-action-menu" onClickCapture={closeActionMenus}>
                  {code.tracking_mode === "tracked" ? <button onClick={() => setChannelCode(code)}>⌁ Channel-specific QR</button> : null}
                  <a href={imageUrl(code, "svg")}>⇩ Download SVG</a>
                  <a href={imageUrl(code, "pdf")}>⇩ Download PDF</a>
                  <button onClick={() => void setActive(code)}>{code.active ? "◌ Deactivate" : "● Reactivate"}</button>
                  <button onClick={() => void clearData(code)}>⌫ Clear scan data</button>
                  <button className="danger" onClick={() => void deleteCode(code)}>🗑 Delete QR permanently</button>
                </div>
              </details>
            </article>
          ))}
          {!pageData.total && !loading ? <div className="qrfy-empty qr-card-grid-empty-v125"><span>⌁</span><h3>No QR codes found</h3><p>Create a new QR or change the filters.</p><Link className="qrfy-button primary" href="/qr">Create QR</Link></div> : null}
        </div>

        <PaginationControls page={pageData.page} pages={pageData.pages} total={pageData.total} start={pageData.start} end={pageData.end} onPageChange={setPage} label="QR codes" />
      </section>

      {previewCode ? <div className="qr-modal-backdrop" role="presentation" onMouseDown={(event: { target: EventTarget | null; currentTarget: HTMLDivElement }) => { if (event.target === event.currentTarget) setPreviewCode(null); }}>
        <section className="qr-preview-modal-v125" role="dialog" aria-modal="true" aria-labelledby="qr-preview-title">
          <button className="qr-modal-close" onClick={() => setPreviewCode(null)} aria-label="Close">×</button>
          <p className="qrfy-kicker">Large QR preview</p>
          <h2 id="qr-preview-title">{previewCode.name}</h2>
          <img src={imageUrl(previewCode, "png", undefined, false)} alt={`Large QR code for ${previewCode.name}`} />
          <p>{destination(previewCode)}</p>
          <div className="qr-preview-actions-v125"><a className="qrfy-button primary" href={imageUrl(previewCode, "png")}>Download PNG</a><a className="qrfy-button secondary" href={imageUrl(previewCode, "svg")}>SVG</a><a className="qrfy-button secondary" href={imageUrl(previewCode, "pdf")}>PDF</a><button className="qrfy-button secondary" onClick={() => void copyQrLink(previewCode)}>Copy QR Link</button></div>
        </section>
      </div> : null}

      {channelCode ? <div className="qr-modal-backdrop" role="presentation" onMouseDown={(event: { target: EventTarget | null; currentTarget: HTMLDivElement }) => { if (event.target === event.currentTarget) setChannelCode(null); }}>
        <section className="qr-channel-modal" role="dialog" aria-modal="true" aria-labelledby="channel-title">
          <button className="qr-modal-close" onClick={() => setChannelCode(null)} aria-label="Close">×</button>
          <p className="qrfy-kicker">Exact source attribution</p>
          <h2 id="channel-title">Download a channel-specific QR</h2>
          <p>Use a different tagged QR image for each distribution channel. Scans from that image are recorded with an <strong>Exact</strong> source tag.</p>
          <div className="qr-channel-grid">
            {CHANNELS.map((item) => <button key={item.value} className={channel === item.value ? "selected" : ""} onClick={() => setChannel(item.value)}><i>{item.icon}</i><span><strong>{item.label}</strong><small>{item.note}</small></span></button>)}
          </div>
          <div className="qr-modal-footer"><label>Format<select value={channelFormat} onChange={(e: ChangeEvent<HTMLSelectElement>) => setChannelFormat(e.target.value as "png" | "svg" | "pdf")}><option value="png">PNG · sharing</option><option value="svg">SVG · print/design</option><option value="pdf">PDF · document</option></select></label><button className="qrfy-button primary" onClick={downloadChannelVariant}>Download tagged QR</button></div>
          <small className="qr-data-note">If the same untagged QR image is copied between apps, the scanner browser may not reveal where the image came from. In that case the source is shown as Detected or Direct/Unknown instead of inventing a platform.</small>
        </section>
      </div> : null}

      {loading ? <div className="qrfy-loading-float">Loading QR library…</div> : null}
    </main>
  );
}
