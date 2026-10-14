import Link from "next/link";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { SyncAllButton } from "@/components/sync-all-button";
import { formatDateTime } from "@/lib/format";
import { getChanges, getChangeSummary, getSourceAnalysis, getSources } from "@/lib/api";
import type { ChangeRecord } from "@/lib/types";

type SearchParams = Promise<{ period?: string; type?: string; source?: string; tab?: string; page?: string; view?: string }>;

export const metadata = { title: "Sheet Updates" };

function linkFor(params: Awaited<SearchParams>, updates: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
  for (const [key, value] of Object.entries(updates)) {
    if (value === undefined || value === "") query.delete(key); else query.set(key, String(value));
  }
  return `?${query.toString()}`;
}

// Keep this strict-safe: RegExp capture groups are string | undefined when
// noUncheckedIndexedAccess is enabled in the real Windows build.
function cellParts(coordinate: string): { row: string; column: string; cell: string } {
  const match = /^([A-Za-z]+)(\d+)$/.exec(coordinate ?? "");
  if (!match) return { row: coordinate.replace(/\D+/g, "") || "—", column: "—", cell: coordinate || "—" };
  const column = match[1] ?? "";
  const row = match[2] ?? "";
  if (!column || !row) return { row: coordinate.replace(/\D+/g, "") || "—", column: "—", cell: coordinate || "—" };
  const upper = column.toUpperCase();
  return { row, column: upper, cell: `${upper}${row}` };
}

function changeLabel(value: string): string {
  if (value === "added") return "Added";
  if (value === "deleted") return "Removed";
  return "Changed";
}

function statusText(status: string): string {
  if (status === "success") return "Checked successfully";
  if (["queued", "downloading", "analyzing"].includes(status)) return "Checking now";
  if (status === "interrupted") return "Previous check stopped; old data kept";
  if (status === "error") return "Check failed; old data kept";
  return "Not checked yet";
}

function extractUrls(value?: string | null): string[] {
  if (!value) return [];
  const matches = value.match(/https?:\/\/[^\s<>'"`]+/gi) ?? [];
  return matches.map((url) => url.replace(/[),.;\]]+$/g, ""));
}

function linkLabel(fieldName: string, url: string): string {
  const text = `${fieldName} ${url}`.toLowerCase();
  if (text.includes("pdf") || url.toLowerCase().includes(".pdf")) return "Open PDF";
  if (text.includes("video") || text.includes("youtube") || text.includes("youtu.be")) return "Open Video";
  if (text.includes("doc")) return "Open Document";
  if (text.includes("meet")) return "Open Meeting";
  return "Open Updated Link";
}

function storyLinks(item: ChangeRecord): Array<{ url: string; label: string }> {
  const seen = new Set<string>();
  const links: Array<{ url: string; label: string }> = [];
  for (const detail of item.details ?? []) {
    // New/after links are primary. If a link was removed, the previous link is
    // still available for audit without forcing the user into the cell view.
    for (const url of extractUrls(detail.new_value)) {
      if (seen.has(url)) continue;
      seen.add(url);
      links.push({ url, label: linkLabel(detail.field_name, url) });
    }
    for (const url of extractUrls(detail.old_value)) {
      if (seen.has(url)) continue;
      seen.add(url);
      links.push({ url, label: `Previous ${linkLabel(detail.field_name, url).replace(/^Open /, "")}` });
    }
  }
  return links.slice(0, 8);
}

function rowPreview(item: ChangeRecord): string {
  const rows = item.affected_rows ?? [];
  if (!rows.length) return "";
  const first = rows.slice(0, 6).join(", ");
  return rows.length > 6 ? `Rows ${first} +${rows.length - 6} more` : `Rows ${first}`;
}

export default async function ChangesPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const period = params.period ?? "today";
  const view = params.view === "cells" ? "cells" : "stories";
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const [data, summary, sources, analyses] = await Promise.all([
    getChanges({ page, pageSize: view === "stories" ? 18 : 35, period, changeType: params.type, sourceId: params.source, sheetName: params.tab, view }),
    getChangeSummary({ period, sourceId: params.source, sheetName: params.tab }),
    getSources(),
    getSourceAnalysis()
  ]);
  const active = sources.filter((source) => ["queued", "downloading", "analyzing"].includes(source.last_sync_status)).length;
  const selectedAnalysis = analyses.find((item) => item.source.id === params.source);
  const tabs = (selectedAnalysis?.profile?.tabs ?? []).filter((tab) => tab.non_empty_cells > 0);
  const exportQuery = new URLSearchParams({ period });
  if (params.type) exportQuery.set("change_type", params.type);
  if (params.source) exportQuery.set("source_id", params.source);
  if (params.tab) exportQuery.set("sheet_name", params.tab);

  return (
    <>
      <PageAutoRefresh minutes={2} />

      <section className="human-page-hero">
        <div>
          <p className="eyebrow">Google Sheet activity</p>
          <h1>What changed in the Sheets?</h1>
          <p>See one clear update for one real change. Cell numbers stay available only when you open technical details.</p>
        </div>
        <div className="human-hero-kpis" aria-label="Sheet update overview">
          <span><strong>{summary.added}</strong> new</span>
          <span><strong>{summary.updated}</strong> changed</span>
          <span><strong>{summary.deleted}</strong> removed</span>
          <span><strong>{summary.total}</strong> logical updates</span>
        </div>
      </section>

      {active ? <div className="sync-queue-note"><strong>{active} Sheet check{active === 1 ? " is" : "s are"} running.</strong> Your previous successful data stays visible while checking completes.</div> : null}

      <section className="sticky-control-deck">
        <div className="compact-toolbar"><SyncAllButton /></div>
        <nav className="human-segmented-control" aria-label="Update period">
          <Link className={period === "today" ? "active" : ""} href={linkFor(params, { period: "today", page: 1 })}>Today</Link>
          <Link className={period === "yesterday" ? "active" : ""} href={linkFor(params, { period: "yesterday", page: 1 })}>Yesterday</Link>
          <Link className={period === "7days" ? "active" : ""} href={linkFor(params, { period: "7days", page: 1 })}>7 days</Link>
          <Link className={period === "all" ? "active" : ""} href={linkFor(params, { period: "all", page: 1 })}>All history</Link>
        </nav>
        <nav className="human-segmented-control human-view-control" aria-label="Display mode">
          <Link className={view === "stories" ? "active" : ""} href={linkFor(params, { view: "stories", page: 1 })}>Simple view</Link>
          <Link className={view === "cells" ? "active" : ""} href={linkFor(params, { view: "cells", page: 1 })}>Technical audit</Link>
        </nav>
      </section>

      <form className="compact-filter-bar" method="get">
        <input type="hidden" name="period" value={period} />
        <input type="hidden" name="view" value={view} />
        <label><span>Change</span><select name="type" defaultValue={params.type ?? ""}><option value="">All changes</option><option value="added">Added</option><option value="updated">Changed</option><option value="deleted">Removed</option></select></label>
        <label><span>Google Sheet</span><select name="source" defaultValue={params.source ?? ""}><option value="">All Sheets</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
        <label><span>Tab</span><select name="tab" defaultValue={params.tab ?? ""} disabled={!params.source}><option value="">{params.source ? "All tabs" : "Choose Sheet first"}</option>{tabs.map((tab) => <option key={tab.name} value={tab.name}>{tab.name}</option>)}</select></label>
        <button className="button primary" type="submit">Apply</button>
        <Link className="button secondary" href={`/changes?period=${period}&view=${view}`}>Clear</Link>
        <a className="button secondary" href={`/backend/api/v1/exports/changes/csv?${exportQuery.toString()}`}>Download CSV</a>
      </form>

      {view === "stories" ? (
        <section className="human-change-feed" aria-label="Human-readable Sheet updates">
          {data.items.map((item) => {
            const links = storyLinks(item);
            const affected = item.affected_count ?? item.affected_rows?.length ?? 1;
            return (
              <article key={item.id} className={`human-change-card human-change-${item.change_type}`}>
                <header>
                  <div className="human-change-badges"><span>{item.category ?? "Sheet update"}</span><span>{changeLabel(item.change_type)}</span>{affected > 1 ? <span>{affected} rows</span> : null}</div>
                  <time>{formatDateTime(item.detected_at)}</time>
                </header>
                <h2>{item.summary ?? "Google Sheet information changed"}</h2>
                {item.impact ? <p>{item.impact}</p> : null}
                <div className="human-change-location"><strong>{item.workbook_name}</strong><span>→</span><strong>{item.sheet_name}</strong>{rowPreview(item) ? <small>{rowPreview(item)}</small> : null}</div>

                {links.length ? <div className="story-link-actions">{links.map((link) => <a key={link.url} href={link.url} target="_blank" rel="noreferrer">{link.label} ↗</a>)}</div> : null}

                <details className="human-change-details">
                  <summary>{affected > 1 ? `View ${affected} affected rows` : `View ${(item.details ?? []).length} field change${(item.details ?? []).length === 1 ? "" : "s"}`} <span>Technical details</span></summary>
                  <div className="human-change-detail-scroll">
                    {(item.details ?? []).map((detail, index) => (
                      <div className="human-field-change" key={`${item.id}-${detail.coordinate ?? index}`}>
                        <div><b>{detail.field_name}</b>{detail.row_number ? <small>Row {detail.row_number}{detail.coordinate ? ` · ${detail.coordinate}` : ""}</small> : detail.coordinate ? <small>{detail.coordinate}</small> : null}</div>
                        <span><small>Before</small>{detail.old_value || "Blank"}</span>
                        <i>→</i>
                        <span><small>After</small>{detail.new_value || "Blank / removed"}</span>
                      </div>
                    ))}
                  </div>
                </details>
              </article>
            );
          })}
          {!data.items.length ? <div className="human-empty-state"><span>✓</span><h2>No changes found</h2><p>The selected Sheets match the previous successful check.</p></div> : null}
        </section>
      ) : (
        <section className="sheet-change-table-wrap">
          <div className="technical-warning"><strong>Technical audit view</strong><span>Use this only when you need exact row, column and cell information.</span></div>
          <table className="sheet-change-table">
            <thead><tr><th>Time</th><th>Google Sheet</th><th>Tab</th><th>Row</th><th>Column</th><th>Cell</th><th>Field</th><th>Change</th><th>Before</th><th>After</th></tr></thead>
            <tbody>
              {data.items.map((item) => {
                const location = cellParts(item.coordinate);
                return <tr key={item.id}><td>{formatDateTime(item.detected_at)}</td><td>{item.workbook_name}</td><td>{item.sheet_name}</td><td>{location.row}</td><td>{location.column}</td><td className="cell-code">{location.cell}</td><td>{item.field_name ?? item.details?.[0]?.field_name ?? "Information"}</td><td className={`change-${item.change_type}`}>{changeLabel(item.change_type)}</td><td className="before-value">{item.old_value || "Blank"}</td><td className="after-value">{item.new_value || "Blank / removed"}</td></tr>;
              })}
            </tbody>
          </table>
          {!data.items.length ? <div className="human-empty-state"><span>✓</span><h2>No cell changes found</h2><p>The selected Sheet and tab match the previous successful check.</p></div> : null}
        </section>
      )}

      {data.pages > 1 ? <nav className="pagination compact-pagination" aria-label="Update pages">{page > 1 ? <Link className="button secondary" href={linkFor(params, { page: page - 1 })}>← Previous</Link> : <span />}<span>Page {data.page} of {data.pages}</span>{page < data.pages ? <Link className="button secondary" href={linkFor(params, { page: page + 1 })}>Next →</Link> : <span />}</nav> : null}

      <details className="collapsed-system-status">
        <summary>Google Sheet connection status <b>{sources.length}</b></summary>
        <div className="source-check-strip">
          {sources.map((source) => <article key={source.id} className={`source-check-${source.last_sync_status}`}><span aria-hidden="true">{source.last_sync_status === "success" ? "✓" : source.last_sync_status === "error" ? "!" : ["queued", "downloading", "analyzing"].includes(source.last_sync_status) ? "↻" : "○"}</span><div><strong>{source.name}</strong><small>{statusText(source.last_sync_status)} · {formatDateTime(source.last_sync_at)}</small>{source.last_error ? <small className="error-copy">{source.last_error}</small> : null}</div></article>)}
        </div>
      </details>
    </>
  );
}
