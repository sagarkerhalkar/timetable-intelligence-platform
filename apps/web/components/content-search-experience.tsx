"use client";

import type { CSSProperties, ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { PUBLIC_API_URL } from "@/lib/api";
import type {
  ContentItem,
  DashboardSummary,
  Paginated,
  SourceAnalysisSummary
} from "@/lib/types";

function typeLabel(value: string): string {
  if (value === "video") return "Video";
  if (value === "pdf") return "PDF";
  if (value === "document") return "Test / Document";
  if (value === "presentation") return "Presentation";
  if (value === "spreadsheet") return "Spreadsheet";
  if (value === "form") return "Form";
  return "Learning link";
}

function contentIcon(type: string): string {
  if (type === "video") return "▶️";
  if (type === "pdf") return "📕";
  if (type === "document") return "📝";
  if (type === "presentation") return "📽️";
  if (type === "spreadsheet") return "📊";
  return "🔗";
}

function uniqueTabs(sourceAnalysis: SourceAnalysisSummary[], sourceId: string): Array<{ name: string; count: number; ready: boolean }> {
  if (!sourceId) return [];
  const source = sourceAnalysis.find((item) => item.source.id === sourceId);
  return (source?.profile?.tabs ?? [])
    .filter((tab) => tab.non_empty_cells > 0)
    .map((tab) => ({
      name: tab.name,
      count: source?.tab_content_counts?.[tab.name] ?? 0,
      ready: tab.search_ready
    }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function ContentSearchExperience({
  initialData,
  dashboard,
  sourceAnalysis,
  initialQuery = "",
  initialType = "",
  initialStream = "",
  initialSource = "",
  initialTab = ""
}: Readonly<{
  initialData: Paginated<ContentItem>;
  dashboard: DashboardSummary;
  sourceAnalysis: SourceAnalysisSummary[];
  initialQuery?: string;
  initialType?: string;
  initialStream?: string;
  initialSource?: string;
  initialTab?: string;
}>) {
  const [query, setQuery] = useState(initialQuery);
  const [type, setType] = useState(initialType);
  const [stream, setStream] = useState(initialStream);
  const [source, setSource] = useState(initialSource);
  const [tab, setTab] = useState(initialTab);
  const [page, setPage] = useState(initialData.page || 1);
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const firstRun = useRef(true);

  const tabs = useMemo(() => uniqueTabs(sourceAnalysis, source), [source, sourceAnalysis]);
  const selectedAnalysis = sourceAnalysis.find((item) => item.source.id === source);
  const selectedSource = selectedAnalysis?.source;
  const selectedTab = tabs.find((item) => item.name === tab);

  const parameters = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "18" });
    if (query.trim()) params.set("query", query.trim());
    if (type) params.set("content_type", type);
    if (stream) params.set("stream", stream);
    if (source) params.set("source_id", source);
    if (tab) params.set("sheet_name", tab);
    return params;
  }, [page, query, source, stream, tab, type]);

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${PUBLIC_API_URL}/api/v1/content?${parameters.toString()}`, {
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok) throw new Error("Search service is unavailable.");
        const nextData = await response.json() as Paginated<ContentItem>;
        setData(nextData);
        const browserQuery = new URLSearchParams();
        if (query.trim()) browserQuery.set("q", query.trim());
        if (type) browserQuery.set("type", type);
        if (stream) browserQuery.set("stream", stream);
        if (source) browserQuery.set("source", source);
        if (tab) browserQuery.set("tab", tab);
        if (page > 1) browserQuery.set("page", String(page));
        window.history.replaceState(null, "", `/content${browserQuery.size ? `?${browserQuery.toString()}` : ""}`);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "Search failed.");
      } finally {
        setLoading(false);
      }
    }, query.trim() ? 220 : 60);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [parameters, page, query, source, stream, tab, type]);

  function chooseQuery(value: string) {
    setQuery(value);
    setPage(1);
  }

  function changeSource(value: string) {
    setSource(value);
    setTab("");
    setPage(1);
  }

  function clearAll() {
    setQuery("");
    setStream("");
    setType("");
    setSource("");
    setTab("");
    setPage(1);
  }

  return (
    <>
      <section className="search-command-v1">
        <div className="search-command-copy">
          <p className="eyebrow">Search every connected Google Sheet</p>
          <h1>Find videos, PDFs and test papers</h1>
          <p>
            Type one word in English, Hindi or Sanskrit. For example, typing <strong>kabir</strong>
            also finds <strong>कबीर</strong>.
          </p>
        </div>
        <div className="search-live-counts">
          <span><strong>{dashboard.videos.toLocaleString("en-IN")}</strong> videos</span>
          <span><strong>{dashboard.pdfs.toLocaleString("en-IN")}</strong> PDFs</span>
          <span><strong>{dashboard.content_items.toLocaleString("en-IN")}</strong> all files</span>
        </div>
        <label className="instant-search-box" htmlFor="instant-search">
          <span aria-hidden="true">🔎</span>
          <input
            id="instant-search"
            autoComplete="off"
            value={query}
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Try: kabir, कबीर, संस्कृत, प्रकाश, economics…"
          />
          {query ? <button type="button" onClick={() => chooseQuery("")} aria-label="Clear search">×</button> : null}
        </label>
        <div className="search-status-line" role="status">
          {loading ? <><span className="search-spinner" /> Searching selected Google Sheet…</> : error ? (
            <strong className="search-error">{error}</strong>
          ) : (
            <>
              <strong>{data.total.toLocaleString("en-IN")}</strong> result{data.total === 1 ? "" : "s"}
              {data.search_ms ? ` · ${data.search_ms} ms` : ""}
              {selectedSource ? ` · ${selectedSource.name}` : " · all Google Sheets"}
            </>
          )}
        </div>
        <div className="search-example-row">
          <span>Try:</span>
          {["kabir", "कबीर", "संस्कृत", "political", "physics", "test paper"].map((value) => (
            <button type="button" key={value} onClick={() => chooseQuery(value)}>{value}</button>
          ))}
        </div>
      </section>

      <section className="search-filter-bar search-filter-bar-v105" aria-label="Search filters">
        <div className="file-type-buttons">
          <button className={!type ? "active" : ""} type="button" onClick={() => { setType(""); setPage(1); }}>All files</button>
          <button className={type === "video" ? "active" : ""} type="button" onClick={() => { setType("video"); setPage(1); }}>▶ Videos</button>
          <button className={type === "pdf" ? "active" : ""} type="button" onClick={() => { setType("pdf"); setPage(1); }}>📕 PDFs</button>
          <button className={type === "document" ? "active" : ""} type="button" onClick={() => { setType("document"); setPage(1); }}>📝 Tests</button>
          <button className={type === "presentation" ? "active" : ""} type="button" onClick={() => { setType("presentation"); setPage(1); }}>📽️ Slides</button>
        </div>
        <div className="sheet-search-filters">
          <label>
            <span>Google Sheet</span>
            <select value={source} onChange={(event: ChangeEvent<HTMLSelectElement>) => changeSource(event.target.value)}>
              <option value="">All connected Sheets</option>
              {sourceAnalysis.map((item) => (
                <option key={item.source.id} value={item.source.id}>
                  {item.source.name} ({item.content_count.toLocaleString("en-IN")})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Tab</span>
            <select
              value={tab}
              disabled={!source}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => { setTab(event.target.value); setPage(1); }}
            >
              <option value="">{source ? "All tabs in this Sheet" : "Choose a Google Sheet first"}</option>
              {tabs.map((item) => <option key={item.name} value={item.name}>{item.name} ({item.count}){item.ready ? "" : " — needs setup"}</option>)}
            </select>
          </label>
          <label>
            <span>Stream</span>
            <select value={stream} onChange={(event: ChangeEvent<HTMLSelectElement>) => { setStream(event.target.value); setPage(1); }}>
              <option value="">All streams</option>
              <option>Commerce</option>
              <option>Science</option>
              <option>Humanities</option>
              <option>Nirmaan</option>
            </select>
          </label>
        </div>
      </section>

      <section className="search-coverage-strip">
        {selectedAnalysis ? (
          <>
            <div><strong>{tab ? (selectedTab?.count ?? data.total) : selectedAnalysis.content_count.toLocaleString("en-IN")}</strong><span>{tab ? `linked records found in ${tab}` : "records indexed in this Sheet"}</span></div>
            <div><strong>{selectedAnalysis.search_ready_tabs}</strong><span>tabs ready for Search</span></div>
            <div className={selectedAnalysis.needs_setup_tabs ? "needs-attention" : ""}><strong>{selectedAnalysis.needs_setup_tabs}</strong><span>tabs need clearer headings</span></div>
            <a href="/sources">See exactly what each tab needs →</a>
          </>
        ) : (
          <>
            <div><strong>{sourceAnalysis.length}</strong><span>connected Google Sheets</span></div>
            <div><strong>{sourceAnalysis.reduce((sum, item) => sum + item.search_ready_tabs, 0)}</strong><span>tabs ready for Search</span></div>
            <div><strong>{sourceAnalysis.reduce((sum, item) => sum + item.needs_setup_tabs, 0)}</strong><span>tabs need setup</span></div>
            <a href="/sources">Check Sheet readiness →</a>
          </>
        )}
      </section>

      {(query || source || tab || stream || type) ? (
        <section className="active-search-filters">
          <div><strong>Searching inside:</strong>
            {query ? <span>Word: {query}</span> : null}
            {selectedSource ? <span>Sheet: {selectedSource.name}</span> : <span>All Google Sheets</span>}
            {tab ? <span>Tab: {tab}</span> : null}
            {stream ? <span>Stream: {stream}</span> : null}
            {type ? <span>Type: {typeLabel(type)}</span> : null}
          </div>
          <button type="button" onClick={clearAll}>Clear every filter</button>
        </section>
      ) : null}

      {data.items.length ? (
        <>
          <section className="instant-result-grid" aria-busy={loading}>
            {data.items.map((item, index) => (
              <article
                className={`instant-result-card type-${item.content_type}`}
                key={item.id}
                style={{ "--card-index": index % 12 } as CSSProperties}
              >
                <div className="instant-result-icon" aria-hidden="true">{contentIcon(item.content_type)}</div>
                <div className="instant-result-main">
                  <div className="search-source-breadcrumb">
                    <span>{item.workbook_name}</span>
                    <b>→</b>
                    <span>{item.sheet_name}</span>
                  </div>
                  <div className="friendly-meta">
                    {item.stream ? <span>{item.stream}</span> : null}
                    {item.class_name ? <span>{item.class_name}</span> : null}
                    {item.batch ? <span>{item.batch}</span> : null}
                    <span>{typeLabel(item.content_type)}</span>
                  </div>
                  <h2>{item.title}</h2>
                  <strong>{item.subject ?? "Subject not named"}</strong>
                  {item.topic ? <p>{item.topic}</p> : null}
                  {item.teacher ? <small>Prepared by {item.teacher}</small> : null}
                  {item.record_kind === "structured_link" ? <small className="link-discovery-note">✓ Link found directly in the Sheet, even when its column is named Remarks or another custom heading.</small> : null}
                  {item.record_kind === "test" ? (
                    <div className="test-search-statuses">
                      <span><small>App Status</small><b>{item.status || "Not updated"}</b></span>
                      <span><small>Test Date</small><b>{item.test_date || "Not scheduled"}</b></span>
                      <span><small>Result Dashboard</small><b>{item.result_dashboard || "Remaining"}</b></span>
                      <span><small>Video Solution</small><b>{item.video_solution_update || "Remaining"}</b></span>
                    </div>
                  ) : null}
                  <div className="instant-result-actions">
                    {item.url ? <a className="button primary compact" href={item.url} target="_blank" rel="noreferrer">
                      Open {typeLabel(item.content_type)} ↗
                    </a> : <span className="status-pill warning">File link is not added in the Sheet</span>}
                    <details>
                      <summary>Show Sheet location (admin only)</summary>
                      <small>{item.workbook_name} → {item.sheet_name} → row {item.source_row}</small>
                    </details>
                  </div>
                </div>
              </article>
            ))}
          </section>
          {data.pages > 1 ? (
            <nav className="instant-pagination">
              <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => Math.max(1, value - 1))}>← Previous</button>
              <span>Page {data.page} of {data.pages}</span>
              <button type="button" disabled={page >= data.pages || loading} onClick={() => setPage((value) => value + 1)}>Next →</button>
            </nav>
          ) : null}
        </>
      ) : !loading ? (
        <section className="search-empty-v1">
          <span>🔎</span>
          <h2>No matching file yet</h2>
          <p>Try one shorter word, choose another Google Sheet, or open Google Sheets to check whether this tab is marked Ready for Search.</p>
          <button className="button secondary" type="button" onClick={clearAll}>Clear search</button>
        </section>
      ) : null}
    </>
  );
}
