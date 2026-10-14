import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { PageHeading } from "@/components/page-heading";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { TimetableCards } from "@/components/timetable-cards";
import { UniversalTimetable } from "@/components/universal-timetable";
import { WeekTimetable } from "@/components/week-timetable";
import { getTimetable } from "@/lib/api";
import { formatFullDate, indiaDateISO, indiaWeekDates } from "@/lib/format";

type SearchParams = Promise<{
  date?: string;
  stream?: string;
  class?: string;
  subject?: string;
  view?: string;
}>;

export const metadata = { title: "Weekly Timetable" };

export default async function TimetablePage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const today = indiaDateISO();
  const view = params.date ? "day" : (params.view ?? "week");
  const weekDates = indiaWeekDates(params.date ?? today);
  const weekStart = weekDates[0] ?? today;
  const weekEnd = weekDates[6] ?? weekStart;
  const selectedDate =
    params.date ??
    (view === "today" ? today : view === "tomorrow" ? indiaDateISO(1) : undefined);
  const showWeek = view === "week";
  const showNext = view === "next";

  const data = await getTimetable({
    page: 1,
    pageSize: showWeek ? 1000 : 250,
    classDate: selectedDate,
    dateFrom: showWeek ? weekStart : undefined,
    dateTo: showWeek ? weekEnd : undefined,
    stream: params.stream,
    className: params.class,
    subject: params.subject,
    latest: false,
    upcoming: showNext
  });

  const displayedDate = data.items.find((item) => item.class_date)?.class_date ?? selectedDate ?? null;
  const title = showWeek
    ? "Weekly Timetable"
    : showNext
      ? "Next Available Timetable"
      : displayedDate
        ? formatFullDate(displayedDate)
        : "Timetable";
  const exportQuery = showWeek
    ? `?date_from=${encodeURIComponent(weekStart)}&date_to=${encodeURIComponent(weekEnd)}`
    : displayedDate
      ? `?class_date=${encodeURIComponent(displayedDate)}`
      : "";

  return (
    <>
      <PageAutoRefresh minutes={5} />
      <div className="auto-refresh-note">Live page refresh every 5 minutes · Google Sheets checked every 30 minutes</div>
      <PageHeading
        eyebrow="Universal timetable"
        title={title}
        description={showWeek
          ? "See all seven days in one short strip. Select any day to see its classes below."
          : "Classes starting together are grouped in one time row."}
        actions={<>
          <a className="button secondary" href={`/backend/api/v1/exports/timetable/pdf${exportQuery}`}>Download PDF</a>
          <a className="button primary" href={`/backend/api/v1/exports/timetable/xlsx${exportQuery}`}>Download Excel</a>
        </>}
      />

      <nav className="universal-view-tabs" aria-label="Timetable view">
        <Link className={view === "today" ? "active" : undefined} href="/timetable?view=today">Today</Link>
        <Link className={showWeek ? "active" : undefined} href="/timetable?view=week">This week</Link>
        <Link className={view === "tomorrow" ? "active" : undefined} href="/timetable?view=tomorrow">Tomorrow</Link>
        <Link className={showNext ? "active" : undefined} href="/timetable?view=next">Next schedule</Link>
      </nav>

      <details className="friendly-filter-panel" open={Boolean(params.stream || params.class || params.subject || params.date)}>
        <summary>Find a date, stream, class or subject</summary>
        <form className="friendly-filter-form" method="get">
          <label><span>Exact date</span><input type="date" name="date" defaultValue={params.date ?? ""} /></label>
          <label><span>Stream</span><select name="stream" defaultValue={params.stream ?? ""}><option value="">All streams</option><option>Commerce</option><option>Science</option><option>Humanities</option><option>Nirmaan</option></select></label>
          <label><span>Class</span><select name="class" defaultValue={params.class ?? ""}><option value="">All classes</option><option>Class 7</option><option>Class 8</option><option>Class 11</option><option>Class 12</option></select></label>
          <label><span>Subject</span><input name="subject" defaultValue={params.subject ?? ""} placeholder="Economics, Biology…" /></label>
          <button className="button primary" type="submit">Show timetable</button>
          <Link className="button secondary" href="/timetable?view=week">Clear</Link>
        </form>
      </details>

      {data.items.length ? (
        showWeek
          ? <WeekTimetable items={data.items} dates={weekDates} />
          : <UniversalTimetable items={data.items} title={displayedDate ? formatFullDate(displayedDate) : "Schedule"} />
      ) : (
        <section className="panel">
          <EmptyState
            icon="📅"
            title="No matching classes"
            description="Choose another date or clear the filters. Only verified timetable rows are shown."
            href="/timetable?view=week"
            action="Open this week"
          />
        </section>
      )}

      {!showWeek && data.total > data.items.length ? (
        <details className="legacy-card-view">
          <summary>Show detailed source cards</summary>
          <TimetableCards items={data.items} />
        </details>
      ) : null}
    </>
  );
}
