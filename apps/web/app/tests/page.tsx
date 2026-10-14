import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { TestTabSwitcher } from "@/components/test-tab-switcher";
import { getTestMonitor, getTestTabCounts } from "@/lib/api";
import type { TestRecord, TestStatusBucket } from "@/lib/types";

type SearchParams = Promise<{ tab?: string }>;

export const metadata = { title: "Sunday Test Readiness" };

function formatDate(value: string): string {
  const date = new Date(value.includes("T") ? value : `${value}T00:00:00+05:30`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-IN", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
}

function done(value?: string | null): boolean {
  return /\b(done|complete|completed|uploaded|live|yes|ok)\b/i.test(value ?? "");
}

function TestTitle({ item }: Readonly<{ item: TestRecord }>) {
  return <>{item.topic ?? item.document_title ?? item.pdf_title ?? item.chapter_number ?? "Test name not added"}</>;
}

function parseTestDate(value: string): Date | null {
  const cleaned = value.replace(/\b(done|completed?)\b/gi, "").trim().replace(/^[ -]+|[ -]+$/g, "");
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(cleaned);
  if (iso) {
    const year = iso[1] ?? "";
    const month = iso[2] ?? "";
    const day = iso[3] ?? "";
    if (year && month && day) return new Date(`${year}-${month}-${day}T00:00:00+05:30`);
  }
  const indian = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/.exec(cleaned);
  if (indian) {
    const day = indian[1] ?? "";
    const month = indian[2] ?? "";
    const year = indian[3] ?? "";
    if (day && month && year) return new Date(`${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}T00:00:00+05:30`);
  }
  const parsed = new Date(cleaned);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function sourceDateNote(item: TestRecord, sunday: string): string {
  const value = (item.test_date_status ?? "").trim();
  if (!value) return "No Test Date in Sheet — Sunday cycle inferred from upload time";
  const parsed = parseTestDate(value);
  if (!parsed) return `Sheet Test Date: ${value}`;
  const source = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "2-digit", month: "short" }).format(parsed);
  const sundayDate = new Date(`${sunday}T00:00:00+05:30`);
  const sundayLabel = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "2-digit", month: "short" }).format(sundayDate);
  const sourceIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(parsed);
  return sourceIso === sunday ? `Sheet Test Date: ${source}` : `Sheet Test Date: ${source} → counted for ${sundayLabel}`;
}

function StatusPill({ value }: Readonly<{ value?: string | null }>) {
  return <span className={done(value) ? "human-status-ready" : "human-status-action"}>{done(value) ? "Ready" : value || "Action needed"}</span>;
}

function ActionTest({ item, sunday }: Readonly<{ item: TestRecord; sunday: string }>) {
  return (
    <article className="sunday-action-item">
      <div className="sunday-action-main">
        <span>{item.sheet_name}</span>
        <h3>{item.class_name ?? item.course ?? "Class not named"} · {item.subject ?? "Subject not named"}</h3>
        <p><TestTitle item={item} /></p>
        <small>{sourceDateNote(item, sunday)}</small>
      </div>
      <div className="sunday-action-state"><StatusPill value={item.app_status} /><small>App Status</small></div>
    </article>
  );
}

function PendingList({ title, copy, items, field }: Readonly<{ title: string; copy: string; items: TestRecord[]; field: "app_status" | "result_dashboard" | "video_solution_update" }>) {
  return (
    <details className="human-collapsible-panel">
      <summary><div><b>{title}</b><span>{copy}</span></div><strong>{items.length}</strong></summary>
      {items.length ? <div className="human-pending-list">{items.slice(0, 100).map((item) => <article key={`${field}-${item.id}`}><div><span>{item.sheet_name}</span><b>{item.class_name ?? item.course ?? "Class missing"} · {item.subject ?? "Subject missing"}</b><small><TestTitle item={item} /> · Row {item.source_row}</small></div><StatusPill value={item[field]} /></article>)}</div> : <div className="human-inline-success">✓ Nothing pending here.</div>}
    </details>
  );
}

function StatusMini({ bucket, label }: Readonly<{ bucket: TestStatusBucket; label: string }>) {
  const percent = bucket.total ? Math.round((bucket.done / bucket.total) * 100) : 100;
  return <article className={bucket.pending ? "human-mini-card needs-attention" : "human-mini-card"}><span>{label}</span><strong>{bucket.done}/{bucket.total}</strong><small>{bucket.pending ? `${bucket.pending} need action` : "Complete"} · {percent}%</small></article>;
}

function CountList({ title, values }: Readonly<{ title: string; values: Record<string, number> }>) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return <div className="human-count-list"><b>{title}</b><div>{entries.length ? entries.map(([name, count]) => <span key={name}>{name}<strong>{count}</strong></span>) : <small>No data</small>}</div></div>;
}

export default async function TestsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const selectedTab = params.tab ?? "";
  const [data, tabCounts] = await Promise.all([
    getTestMonitor(undefined, selectedTab || undefined, true),
    getTestTabCounts(),
  ]);
  const allTabTotal = Object.values(tabCounts).reduce((sum, count) => sum + count, 0);

  const readiness = data.cycle.total_tests ? Math.round((data.cycle.app_done / data.cycle.total_tests) * 100) : 100;
  const sundayNeedsAction = data.upcoming_sunday_tests.filter((item) => !done(item.app_status));
  const sundayReady = Math.max(0, data.cycle.total_tests - sundayNeedsAction.length);
  const quality = data.summary.data_quality;
  const qualityIssues = quality.missing_course + quality.missing_class + quality.missing_subject + quality.missing_topic + quality.missing_clickable_link + quality.missing_app_status + quality.missing_test_date;

  return (
    <>
      <PageAutoRefresh minutes={5} />

      <section className="human-page-hero test-human-hero">
        <div>
          <p className="eyebrow">Sunday Test Readiness</p>
          <h1>{readiness}% ready for {formatDate(data.cycle.sunday_date)}</h1>
          <p>{data.cycle.total_tests ? `${data.cycle.total_tests} tests belong to this Sunday cycle. ${sundayNeedsAction.length ? `${sundayNeedsAction.length} still need attention.` : "No Sunday App Status work is pending."}` : "No test is assigned to this Sunday in the selected view."}</p>
          <small className="rule-note">Rule: any Sheet Test Date from Monday to Saturday is counted for that same week’s Sunday. The original Sheet date remains visible below.</small>
        </div>
        <div className="readiness-score" aria-label={`${readiness}% ready`}><strong>{readiness}%</strong><span>Sunday ready</span></div>
      </section>

      <TestTabSwitcher selectedTab={selectedTab} counts={tabCounts} total={allTabTotal} />

      <section className="human-readiness-kpis" aria-label="Sunday readiness summary">
        <article><span>Sunday tests</span><strong>{data.cycle.total_tests}</strong><small>{selectedTab || "All monitored tabs"}</small></article>
        <article className="ready"><span>Ready</span><strong>{sundayReady}</strong><small>App Status complete</small></article>
        <article className={sundayNeedsAction.length ? "attention" : "ready"}><span>Need attention</span><strong>{sundayNeedsAction.length}</strong><small>Before Sunday</small></article>
        <article><span>Subjects</span><strong>{Object.keys(data.cycle.subject_counts).length}</strong><small>This Sunday</small></article>
      </section>

      <section className="human-action-board">
        <header><div><p className="eyebrow">What needs action now?</p><h2>{sundayNeedsAction.length ? `${sundayNeedsAction.length} Sunday tests still need App Status work` : "Sunday readiness is complete"}</h2></div><span className={sundayNeedsAction.length ? "attention-chip" : "ready-chip"}>{sundayNeedsAction.length ? "Action required" : "Ready"}</span></header>
        {sundayNeedsAction.length ? <div className="sunday-action-list">{sundayNeedsAction.slice(0, 8).map((item) => <ActionTest key={item.id} item={item} sunday={data.cycle.sunday_date} />)}</div> : <div className="human-empty-state compact"><span>✓</span><h3>No immediate Sunday action</h3><p>All tests in this view are marked ready in App Status.</p></div>}
        {sundayNeedsAction.length > 8 ? <details className="inline-more"><summary>Show {sundayNeedsAction.length - 8} more tests</summary><div className="sunday-action-list">{sundayNeedsAction.slice(8).map((item) => <ActionTest key={item.id} item={item} sunday={data.cycle.sunday_date} />)}</div></details> : null}
      </section>

      <section className="human-cycle-strip" aria-label="Weekly test cycle">
        <div><span>Mon–Sat</span><b>Tests are collected for Sunday</b><small>{formatDateTime(data.cycle.window_start)} → {formatDateTime(data.cycle.window_end)}</small></div>
        <div><span>Sunday</span><b>Test day</b><small>{formatDate(data.cycle.sunday_date)}</small></div>
        <div><span>Monday 6 PM</span><b>Result Dashboard</b><small>{formatDateTime(data.cycle.result_deadline)}</small></div>
        <div><span>Tuesday 6 PM</span><b>Video Solution</b><small>{formatDateTime(data.cycle.video_deadline)}</small></div>
      </section>

      <details className="human-collapsible-panel sunday-list-panel">
        <summary><div><b>All tests going this Sunday</b><span>Open only when you need the full list.</span></div><strong>{data.cycle.total_tests}</strong></summary>
        {data.upcoming_sunday_tests.length ? <div className="responsive-table human-test-table"><table><thead><tr><th>#</th><th>Class / Subject</th><th>Test</th><th>Original Sheet date</th><th>App Status</th></tr></thead><tbody>{data.upcoming_sunday_tests.map((item, index) => <tr key={item.id}><td>{index + 1}</td><td><b>{item.class_name ?? item.course ?? "Class missing"}</b><small>{item.subject ?? "Subject missing"} · {item.sheet_name}</small></td><td><TestTitle item={item} /></td><td>{sourceDateNote(item, data.cycle.sunday_date)}</td><td><StatusPill value={item.app_status} /></td></tr>)}</tbody></table></div> : <div className="human-inline-success">No test belongs to this Sunday in the selected view.</div>}
      </details>

      <details className="human-collapsible-panel">
        <summary><div><b>After-Sunday work</b><span>Result Dashboard and Video Solution deadlines.</span></div><strong>{data.summary.result_dashboard.pending + data.summary.video_solution.pending}</strong></summary>
        <div className="human-mini-grid"><StatusMini bucket={data.summary.result_dashboard} label="Result Dashboard" /><StatusMini bucket={data.summary.video_solution} label="Video Solution" /></div>
        <PendingList title="Result Dashboard remaining" copy="Due tests not marked complete." items={data.pending_result} field="result_dashboard" />
        <PendingList title="Video Solution remaining" copy="Due tests not marked complete." items={data.pending_video} field="video_solution_update" />
      </details>

      <details className="human-collapsible-panel">
        <summary><div><b>Test analytics</b><span>Coverage and totals. Hidden by default to keep this page easy to read.</span></div><strong>{data.summary.total_tests}</strong></summary>
        <div className="human-mini-grid"><StatusMini bucket={data.summary.app_status} label="App Status" /><article className="human-mini-card"><span>Clickable files</span><strong>{data.summary.tests_with_clickable_files}</strong><small>{data.summary.tests_without_clickable_files} missing links</small></article><article className="human-mini-card"><span>New in 7 days</span><strong>{data.summary.new_tests_7days}</strong><small>Recently discovered</small></article></div>
        <div className="human-analysis-columns"><CountList title="This Sunday by subject" values={data.cycle.subject_counts} /><CountList title="All tests by subject" values={data.summary.subject_counts} /><CountList title="Classes" values={data.summary.class_counts} /><CountList title="Courses / batches" values={data.summary.course_counts} /></div>
        <PendingList title="All App Status remaining" copy="All monitored tests not marked complete, including tests outside this Sunday." items={data.pending_app} field="app_status" />
      </details>

      <details className="human-collapsible-panel">
        <summary><div><b>Sheet quality / technical checks</b><span>Only open this when something is missing or looks wrong.</span></div><strong>{qualityIssues}</strong></summary>
        <div className="quality-compact-grid">
          <span>Course missing <b>{quality.missing_course}</b></span><span>Class missing <b>{quality.missing_class}</b></span><span>Subject missing <b>{quality.missing_subject}</b></span><span>Topic missing <b>{quality.missing_topic}</b></span><span>Clickable link missing <b>{quality.missing_clickable_link}</b></span><span>App Status blank <b>{quality.missing_app_status}</b></span><span>Test Date blank <b>{quality.missing_test_date}</b></span><span>Result blank <b>{quality.missing_result_dashboard}</b></span><span>Video Solution blank <b>{quality.missing_video_solution}</b></span>
        </div>
      </details>

      <div className="human-inline-note">Notification setup is available from the Notifications page. Keeping it out of this screen makes Test Monitor faster.</div>
    </>
  );
}
