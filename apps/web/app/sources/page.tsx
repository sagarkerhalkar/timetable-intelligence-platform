import Link from "next/link";
import { OfficialSourcesButton } from "@/components/official-sources-button";
import { PageHeading } from "@/components/page-heading";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { SourceAutoRefresh } from "@/components/source-auto-refresh";
import { SourceConnectForm } from "@/components/source-connect-form";
import { SourceDeleteButton } from "@/components/source-delete-button";
import { SyncSourceButton } from "@/components/sync-source-button";
import { getSourceAnalysis } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { SourceAnalysisSummary, TabProfile } from "@/lib/types";

export const metadata = { title: "Google Sheets" };

function statusLabel(status: string): string {
  if (status === "success" || status === "local_import") return "Ready";
  if (status === "error") return "Needs attention";
  if (status === "interrupted") return "Previous check stopped — old data kept";
  if (status === "queued") return "Waiting to check";
  if (status === "downloading") return "Reading sheet";
  if (status === "analyzing") return "Understanding tabs";
  return "Not checked yet";
}

function statusTone(status: string): string {
  if (status === "success" || status === "local_import") return "good";
  if (status === "error") return "bad";
  if (status === "interrupted") return "warning";
  if (["queued", "downloading", "analyzing"].includes(status)) return "warning";
  return "neutral";
}

function tabCounts(tabs: TabProfile[]) {
  return tabs.reduce((counts, tab) => {
    if (tab.kind === "timetable") counts.timetable += 1;
    else if (tab.kind === "weekly_planner") counts.planner += 1;
    else if (tab.kind === "content_library") counts.content += 1;
    else if (tab.kind === "mixed") counts.mixed += 1;
    else counts.other += 1;
    return counts;
  }, { timetable: 0, planner: 0, content: 0, mixed: 0, other: 0 });
}

function SourceCard({ analysis }: { analysis: SourceAnalysisSummary }) {
  const { source, profile, timetable_count: classes, content_count: content, test_count: tests } = analysis;
  const counts = tabCounts(profile?.tabs ?? []);
  const active = ["queued", "downloading", "analyzing"].includes(source.last_sync_status);

  return (
    <article className="friendly-source-card">
      <div className="friendly-source-top">
        <div className="source-name-block">
          <span className="sheet-logo" aria-hidden="true">▦</span>
          <div>
            <h2>{source.name}</h2>
            <p>{statusLabel(source.last_sync_status)}</p>
          </div>
        </div>
        <span className={`status-pill ${statusTone(source.last_sync_status)}`}>{active ? "Checking now" : statusLabel(source.last_sync_status)}</span>
      </div>

      {source.last_error ? <div className="friendly-error"><strong>Could not read this sheet.</strong><span>{source.last_error}</span></div> : null}

      <div className="understood-grid" aria-label={`What was understood from ${source.name}`}>
        <div><strong>{profile?.tabs.length ?? 0}</strong><span>tabs found</span></div>
        <div><strong>{classes}</strong><span>classes found</span></div>
        <div><strong>{content}</strong><span>searchable files</span></div>
        <div><strong>{tests}</strong><span>structured tests</span></div>
      </div>

      <div className="plain-understanding">
        <h3>What the app understood</h3>
        {profile ? (
          <ul>
            <li>{analysis.search_ready_tabs} tab{analysis.search_ready_tabs === 1 ? " is" : "s are"} ready for Search</li>
            <li>{analysis.needs_setup_tabs} non-empty tab{analysis.needs_setup_tabs === 1 ? " needs" : "s need"} clearer headings</li>
            <li>{counts.timetable + counts.mixed} timetable or combined tab{counts.timetable + counts.mixed === 1 ? "" : "s"}</li>
            <li>{counts.planner} Weekly Planner tab{counts.planner === 1 ? "" : "s"}</li>
            <li>{counts.content} subject/content tab{counts.content === 1 ? "" : "s"}</li>
          </ul>
        ) : <p>No completed analysis yet. Select Check now.</p>}
      </div>

      <div className="friendly-source-footer">
        <div><small>Last checked</small><strong>{formatDateTime(source.last_sync_at)}</strong></div>
        <div className="source-actions">
          <a className="button secondary compact" href={source.url} target="_blank" rel="noreferrer">Open Google Sheet</a>
          <SyncSourceButton sourceId={source.id} disabled={!source.enabled} />
          <SourceDeleteButton sourceId={source.id} sourceName={source.name} />
        </div>
      </div>

      {profile ? (
        <details className="advanced-sheet-details">
          <summary>See tab-by-tab details</summary>
          <p className="advanced-help">This section is for checking how each tab was classified. Normal users do not need it.</p>
          <div className="friendly-tab-list">
            {profile.tabs.map((tab) => {
              const indexedCount = analysis.tab_content_counts?.[tab.name] ?? 0;
              return (
                <div className={`friendly-tab-row ${tab.search_ready ? "tab-ready" : "tab-needs-setup"}`} key={`${source.id}-${tab.name}`}>
                  <div><strong>{tab.name}</strong><small>{tab.hidden ? "Hidden tab" : "Visible tab"}</small></div>
                  <span>{tab.search_ready ? "Ready for Search" : "Needs clearer headings"}</span>
                  <div><strong>{indexedCount}</strong><small>search records</small></div>
                  {tab.searchable_fields.length ? <small className="detected-fields">Understood: {tab.searchable_fields.map((field) => field.replaceAll("_", " ")).join(", ")}</small> : null}
                  {tab.missing_recommended_fields.length ? <small className="warning-copy">Add or rename: {tab.missing_recommended_fields.join(" · ")}</small> : null}
                  {tab.warnings.length ? <small className="warning-copy">{tab.warnings.join(" · ")}</small> : null}
                </div>
              );
            })}
          </div>
          <details className="technical-details"><summary>Technical information</summary><code>{source.spreadsheet_id}</code><p>{profile.total_non_empty_cells.toLocaleString("en-IN")} populated cells checked.</p></details>
        </details>
      ) : null}
    </article>
  );
}

export default async function SourcesPage() {
  const analyses = await getSourceAnalysis();
  const hasActiveSync = analyses.some(({ source }) => ["queued", "downloading", "analyzing"].includes(source.last_sync_status));
  const ready = analyses.filter(({ source }) => ["success", "local_import"].includes(source.last_sync_status)).length;
  const errors = analyses.filter(({ source }) => source.last_sync_status === "error").length;

  return (
    <>
      <PageAutoRefresh minutes={5} />
      <SourceAutoRefresh active={hasActiveSync} />
      <PageHeading
        eyebrow="Simple connection status"
        title="Google Sheets"
        description="See every connected workbook, what the app understood from each tab, and when it was last checked. New Sheets are handled with the same process."
        actions={<Link className="button secondary" href="/">Back to Today</Link>}
      />

      <section className={`sheet-health-banner ${errors ? "has-error" : ""}`}>
        <div>
          <span className="health-symbol" aria-hidden="true">{errors ? "!" : ready === analyses.length && ready ? "✓" : "↻"}</span>
          <div><h2>{errors ? `${errors} sheet${errors === 1 ? "" : "s"} need attention` : ready === analyses.length && ready ? "All Google Sheets are ready" : "Google Sheets are being checked"}</h2><p>{errors ? "Open the affected card below to see the exact problem." : `${ready} of ${analyses.length} workbooks are ready for timetable and content.`}</p></div>
        </div>
        <OfficialSourcesButton />
      </section>

      <section className="how-it-works" aria-label="How sheet information becomes useful">
        <div><span>1</span><strong>Read every tab</strong><small>Visible and hidden tabs, including newly added Sheets</small></div>
        <div><span>2</span><strong>Understand the headings</strong><small>Course, class, subject, chapter, teacher, file and status</small></div>
        <div><span>3</span><strong>Make it searchable</strong><small>Filter by Google Sheet, tab, language, class and subject</small></div>
      </section>

      {analyses.length ? (
        <section className="sheet-manager panel">
          <div className="panel-title"><div><p className="eyebrow">Connect, check or remove</p><h2>Manage connected Google Sheets</h2><p>Removing a Sheet deletes only its local connection and indexed data. The original Google Sheet is never deleted.</p></div></div>
          <div className="sheet-manager-list">
            {analyses.map(({ source, profile, content_count: content, test_count: tests, timetable_count: classes }) => (
              <article key={`manager-${source.id}`}>
                <div><strong>{source.name}</strong><small>{profile?.tabs.length ?? 0} tabs · {content} search records · {classes} classes · {tests} tests</small></div>
                <div className="source-actions"><a className="button secondary compact" href={source.url} target="_blank" rel="noreferrer">Open Sheet</a><SyncSourceButton sourceId={source.id} disabled={!source.enabled} /><SourceDeleteButton sourceId={source.id} sourceName={source.name} /></div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {analyses.length ? <section className="friendly-source-list">{analyses.map((analysis) => <SourceCard analysis={analysis} key={analysis.source.id} />)}</section> : (
        <section className="panel"><div className="empty-state compact-empty"><span aria-hidden="true">▦</span><h2>No Google Sheets connected</h2><p>Select Connect all four official sheets above. Each connection appears immediately and analysis continues in the background.</p></div></section>
      )}

      <section className="sheet-format-guide panel">
        <div className="panel-title"><div><p className="eyebrow">For any new Google Sheet</p><h2>Headings the app understands automatically</h2></div><span className="status-pill good">No coding needed</span></div>
        <p>A Sheet can use a different column order. The app reads the heading names, not fixed column letters.</p>
        <div className="sheet-format-columns">
          <article><strong>Minimum for useful Search</strong><span>Title / Topic / Chapter</span><span>Subject or Class</span><span>Docs Link / PDF / Video Link / File Link</span></article>
          <article><strong>Recommended details</strong><span>Course or Batch</span><span>Teacher / Made by</span><span>Date, Questions, Duration, Marks</span></article>
          <article><strong>For Test Monitor</strong><span>App Status</span><span>Test Date</span><span>Result Dashboard</span><span>Video Solution Update</span></article>
        </div>
        <p className="sheet-format-note">After connecting a Sheet, open its tab-by-tab details. The app will show <b>Ready for Search</b> or exactly which heading is missing. You do not need to send every new Sheet to us.</p>
      </section>

      <details className="add-sheet-section">
        <summary>Add a different Google Sheet</summary>
        <div className="panel source-connect-panel">
          <div className="panel-title"><div><p className="eyebrow">Optional</p><h2>Add another Google Sheet</h2></div><span className="status-pill neutral">No Google password stored</span></div>
          <SourceConnectForm />
        </div>
      </details>
    </>
  );
}
