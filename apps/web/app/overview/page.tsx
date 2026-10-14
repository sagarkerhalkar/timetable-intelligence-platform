import Link from "next/link";
import { PageHeading } from "@/components/page-heading";
import { StatCard } from "@/components/stat-card";
import { getDashboard, getTimetable } from "@/lib/api";
import { formatDateTime, formatTime } from "@/lib/format";

export default async function DashboardPage() {
  const [dashboard, latest] = await Promise.all([
    getDashboard(),
    getTimetable({ pageSize: 8, latest: true })
  ]);
  const latestDate = latest.items.find((item) => item.class_date)?.class_date ?? null;
  const healthy = dashboard.connected_sources > 0 && dashboard.sync_errors === 0;

  return (
    <>
      <PageHeading
        eyebrow="Global overview"
        title="Timetable control center"
        description="One view of verified sheet analysis, classes, learning content, daily changes and synchronization health."
        actions={<><Link className="button secondary" href="/changes">View daily changes</Link><Link className="button primary" href="/sources">Sheet Intelligence</Link></>}
      />

      <section className="hero-panel" aria-labelledby="sync-title">
        <div className="hero-orb orb-one" aria-hidden="true" />
        <div className="hero-orb orb-two" aria-hidden="true" />
        <div>
          <p className="eyebrow light">Verified workbook engine</p>
          <h2 id="sync-title">{dashboard.connected_sources ? `${dashboard.tabs_scanned} tabs analysed across ${dashboard.connected_sources} workbooks.` : "Connect the four official Google Sheets."}</h2>
          <p>{dashboard.connected_sources ? "Commerce, Science, Humanities and Nirmaan use dedicated timetable-pattern reconciliation instead of generic row guessing." : "The first scan establishes a clean baseline; later scans record only real data changes."}</p>
          <div className="hero-actions"><Link className="button white" href="/sources">Inspect every tab</Link><Link className="text-link" href="/timetable">Open verified timetable →</Link></div>
        </div>
        <div className="sync-sphere" aria-label={healthy ? "Synchronization healthy" : "Synchronization needs review"}>
          <span>{healthy ? "LIVE" : "REVIEW"}</span><strong>{dashboard.connected_sources}</strong><small>sources</small>
        </div>
      </section>

      <section className="stats-grid" aria-label="Platform statistics">
        <StatCard label="Connected sheets" value={dashboard.connected_sources} detail={`${dashboard.tabs_scanned} tabs analysed`} icon="⌗" tone="blue" />
        <StatCard label="Verified classes" value={dashboard.timetable_entries} detail="Deduplicated with source proof" icon="▦" tone="cyan" />
        <StatCard label="Videos and PDFs" value={dashboard.videos + dashboard.pdfs} detail={`${dashboard.videos} videos · ${dashboard.pdfs} PDFs`} icon="◉" tone="violet" />
        <StatCard label="Changes today" value={dashboard.changes_today} detail={dashboard.sync_errors ? `${dashboard.sync_errors} source error(s)` : "Formatting-only edits excluded"} icon="↻" tone="amber" />
      </section>

      <section className="dashboard-grid">
        <article className="panel span-two">
          <div className="panel-title"><div><p className="eyebrow">Latest available schedule</p><h2>{latestDate ?? "No verified timetable yet"}</h2></div><Link href="/timetable">Full timetable →</Link></div>
          {latest.items.length ? (
            <div className="timeline-preview">
              {latest.items.map((item) => (
                <div className="timeline-row" key={item.id}>
                  <time>{formatTime(item.start_time)}</time><span className="timeline-dot" />
                  <div><strong>{item.class_name} · {item.subject}</strong><p>{item.topic ?? `${item.stream ?? ""} ${item.batch ?? ""}`}</p></div>
                </div>
              ))}
            </div>
          ) : <p className="muted-copy">Run Sync from Sheet Intelligence. Unverified template rows are not displayed.</p>}
        </article>

        <article className="panel">
          <div className="panel-title"><div><p className="eyebrow">Live status</p><h2>Sync health</h2></div><span className={`status-pill ${healthy ? "good" : "warning"}`}>{healthy ? "Healthy" : "Review"}</span></div>
          <div className="health-ring"><div><strong>{healthy ? "100" : dashboard.sync_errors}</strong><small>{healthy ? "% verified" : "errors"}</small></div></div>
          <dl className="metric-list"><div><dt>Last successful sync</dt><dd>{formatDateTime(dashboard.last_successful_sync)}</dd></div><div><dt>Tabs analysed</dt><dd>{dashboard.tabs_scanned}</dd></div><div><dt>Source errors</dt><dd>{dashboard.sync_errors}</dd></div></dl>
        </article>

        <article className="panel span-three">
          <div className="panel-title"><div><p className="eyebrow">Learning content</p><h2>Content distribution</h2></div><Link href="/content">Search library →</Link></div>
          <div className="content-bars">
            {[["Video lessons", dashboard.videos], ["PDF notes", dashboard.pdfs], ["Other links", Math.max(0, dashboard.content_items - dashboard.videos - dashboard.pdfs)]].map(([label, value]) => {
              const numericValue = Number(value);
              const width = dashboard.content_items ? Math.max(3, Math.round((numericValue / dashboard.content_items) * 100)) : 3;
              return <div key={String(label)}><div><span>{label}</span><strong>{numericValue}</strong></div><div className="bar-track"><span style={{ width: `${width}%` }} /></div></div>;
            })}
          </div>
        </article>
      </section>
    </>
  );
}
