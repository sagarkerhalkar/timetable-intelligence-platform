import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { UniversalTimetable } from "@/components/universal-timetable";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { getDashboard, getTimetable } from "@/lib/api";
import { formatDateTime, formatFullDate, formatTime, indiaDateISO } from "@/lib/format";

export const metadata = { title: "Today" };

export default async function TodayPage() {
  const today = indiaDateISO();
  const [dashboard, schedule] = await Promise.all([
    getDashboard(),
    getTimetable({ classDate: today, latest: false, pageSize: 100 })
  ]);
  const nextSchedule = schedule.items.length
    ? null
    : await getTimetable({ upcoming: true, latest: false, pageSize: 20 });
  const nextDate = nextSchedule?.items.find((item) => item.class_date)?.class_date ?? null;
  const firstClass = schedule.items[0] ?? null;
  const streams = new Set(schedule.items.map((item) => item.stream).filter(Boolean)).size;
  const timeSlots = new Set(schedule.items.map((item) => item.start_time).filter(Boolean)).size;
  const exportQuery = `?class_date=${encodeURIComponent(today)}`;
  const streamCounts = ["Commerce", "Science", "Humanities", "Nirmaan"].map((stream) => ({
    stream,
    count: schedule.items.filter((item) => item.stream === stream).length
  }));
  const pendingTopics = schedule.items.filter((item) => item.topic?.startsWith("Weekly Planner not updated")).length;

  return (
    <>
      <PageAutoRefresh minutes={5} />
      <div className="auto-refresh-note">Live page refresh every 5 minutes · Google Sheets checked every 30 minutes</div>
      <section className="today-command">
        <div className="today-command-main">
          <div className="today-date-chip"><span>Today</span><strong>{formatFullDate(today)}</strong></div>
          <div className="today-command-title">
            <p className="eyebrow">Everything on one screen</p>
            <h1>Today&apos;s Timetable</h1>
            <p>Classes are grouped by start time, so a child can understand the complete day quickly.</p>
          </div>
        </div>
        <div className="today-facts">
          <div><strong>{schedule.total}</strong><span>classes</span></div>
          <div><strong>{timeSlots}</strong><span>time slots</span></div>
          <div><strong>{streams}</strong><span>streams</span></div>
          <div><strong>{firstClass ? formatTime(firstClass.start_time) : "—"}</strong><span>first class</span></div>
        </div>
        <div className="today-command-actions">
          <a className="button primary compact" href={`/backend/api/v1/exports/timetable/pdf${exportQuery}`}>Download today</a>
          <Link className="button secondary compact" href="/timetable?view=week">Open weekly view</Link>
        </div>
      </section>

      <nav className="universal-view-tabs" aria-label="Timetable shortcuts">
        <Link className="active" href="/">Today</Link>
        <Link href="/timetable?view=week">This week</Link>
        <Link href={`/timetable?date=${indiaDateISO(1)}`}>Tomorrow</Link>
        <Link href="/timetable?view=next">Next schedule</Link>
      </nav>

      {schedule.items.length ? (
        <>
          <section className="today-source-check" aria-label="Today timetable by stream">
            {streamCounts.map((item) => (
              <Link
                className="today-stream-link"
                key={item.stream}
                href={`/timetable?date=${encodeURIComponent(today)}&stream=${encodeURIComponent(item.stream)}`}
                aria-label={`Open today’s ${item.stream} timetable (${item.count} classes)`}
              >
                <b>{item.count}</b>{item.stream}<small>Open →</small>
              </Link>
            ))}
            {pendingTopics ? <p><strong>{pendingTopics} class topics are pending.</strong> The subject and time are shown from the Time Table tab because the dated Weekly Planner has not been updated.</p> : <p><strong>All displayed classes have dated planner topics.</strong></p>}
          </section>
          <UniversalTimetable items={schedule.items} />
        </>
      ) : (
        <section className="panel">
          <EmptyState
            icon="✓"
            title="No class is scheduled today"
            description={nextDate ? `The next available schedule is ${formatFullDate(nextDate)}.` : "The connected sheets do not contain a later verified class yet."}
            href={nextDate ? "/timetable?view=next" : "/sources"}
            action={nextDate ? "Open next schedule" : "Check Google Sheets"}
          />
        </section>
      )}

      <section className="today-footer-strip">
        <article><span>📊</span><div><strong>{dashboard.connected_sources} Google Sheets ready</strong><small>Last checked {formatDateTime(dashboard.last_successful_sync)}</small></div><Link href="/sources">Sheet status</Link></article>
        <article><span>🎬</span><div><strong>{dashboard.videos + dashboard.pdfs} videos and PDFs</strong><small>Search in English, Hindi or Sanskrit</small></div><Link href="/content">Search content</Link></article>
        <article><span>🔔</span><div><strong>{dashboard.changes_today} changes today</strong><small>Compare the live sheets now</small></div><Link href="/changes">Sheet updates</Link></article>
      </section>
    </>
  );
}
