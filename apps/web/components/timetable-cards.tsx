import type { TimetableEntry } from "@/lib/types";
import { formatFullDate, formatTime } from "@/lib/format";

type SubjectStyle = { icon: string; label: string; tone: string };

const SUBJECT_STYLES: Array<[RegExp, SubjectStyle]> = [
  [/account/i, { icon: "🧾", label: "Accountancy", tone: "mint" }],
  [/business|entrepreneur/i, { icon: "💼", label: "Business Studies", tone: "amber" }],
  [/econom/i, { icon: "📈", label: "Economics", tone: "blue" }],
  [/math/i, { icon: "🧮", label: "Mathematics", tone: "violet" }],
  [/physics/i, { icon: "⚛️", label: "Physics", tone: "blue" }],
  [/chem/i, { icon: "🧪", label: "Chemistry", tone: "rose" }],
  [/biology/i, { icon: "🌿", label: "Biology", tone: "mint" }],
  [/political/i, { icon: "🗳️", label: "Political Science", tone: "violet" }],
  [/history/i, { icon: "🏛️", label: "History", tone: "amber" }],
  [/geography|social science|sst/i, { icon: "🌍", label: "Social Science", tone: "blue" }],
  [/psychology/i, { icon: "🧠", label: "Psychology", tone: "rose" }],
  [/sociology/i, { icon: "👥", label: "Sociology", tone: "violet" }],
  [/english/i, { icon: "📖", label: "English", tone: "blue" }],
  [/hindi/i, { icon: "🪷", label: "Hindi", tone: "rose" }],
  [/sanskrit/i, { icon: "🕉️", label: "Sanskrit", tone: "amber" }],
  [/science/i, { icon: "🔬", label: "Science", tone: "mint" }],
  [/physical education/i, { icon: "🏃", label: "Physical Education", tone: "amber" }]
];

function subjectStyle(subject: string | null): SubjectStyle {
  const value = subject ?? "";
  return SUBJECT_STYLES.find(([pattern]) => pattern.test(value))?.[1] ?? {
    icon: "🎓",
    label: subject || "Class",
    tone: "blue"
  };
}

function groupByDate(items: TimetableEntry[]): Array<[string, TimetableEntry[]]> {
  const groups = new Map<string, TimetableEntry[]>();
  for (const item of items) {
    const key = item.class_date ?? "Date pending";
    const group = groups.get(key) ?? [];
    group.push(item);
    groups.set(key, group);
  }
  return [...groups.entries()].map(([key, entries]) => [
    key,
    [...entries].sort((a, b) => (a.start_time ?? "99:99").localeCompare(b.start_time ?? "99:99"))
  ]);
}

function friendlyBatch(batch: string | null): string | null {
  if (!batch) return null;
  return batch
    .replace("Nirmaan New NCERT", "New NCERT")
    .replace("Nirmaan Old NCERT", "Old NCERT")
    .replace("Nirmaan 2.0", "Nirmaan 2.0");
}

export function TimetableCards({ items, compact = false }: { items: TimetableEntry[]; compact?: boolean }) {
  return (
    <div className={compact ? "schedule-groups compact-schedule schedule-v4" : "schedule-groups schedule-v4"}>
      {groupByDate(items).map(([date, entries]) => (
        <section className="schedule-day" key={date}>
          {!compact ? (
            <div className="schedule-day-heading friendly-date-heading">
              <div><span aria-hidden="true">📅</span><h2>{date === "Date pending" ? date : formatFullDate(date)}</h2></div>
              <strong>{entries.length} class{entries.length === 1 ? "" : "es"}</strong>
            </div>
          ) : null}
          <div className="schedule-card-list">
            {entries.map((item, index) => {
              const style = subjectStyle(item.subject);
              const batch = friendlyBatch(item.batch);
              return (
                <article className={`schedule-card schedule-card-v4 tone-${style.tone}`} key={item.id} style={{ "--card-index": index } as React.CSSProperties}>
                  <div className="class-number" aria-label={`Class number ${index + 1}`}>{index + 1}</div>
                  <div className="subject-cube" aria-hidden="true"><span>{style.icon}</span></div>
                  <div className="schedule-time-v4">
                    <small>Starts at</small>
                    <strong>{formatTime(item.start_time)}</strong>
                    {item.end_time ? <span>Ends {formatTime(item.end_time)}</span> : null}
                  </div>
                  <div className="schedule-main schedule-main-v4">
                    <div className="friendly-meta big-meta">
                      <span className={`stream-pill stream-${(item.stream ?? "other").toLowerCase()}`}>{item.stream ?? "General"}</span>
                      <span className="class-chip">{item.class_name ?? "Class"}</span>
                      {batch ? <span className="batch-chip">{batch}</span> : null}
                    </div>
                    <h3>{item.subject ?? style.label}</h3>
                    <div className="lesson-box">
                      <small>Today&apos;s lesson</small>
                      <p>{item.topic ?? "The topic has not been added to the planner yet."}</p>
                    </div>
                    {item.teacher ? <p className="teacher-line"><span aria-hidden="true">👩‍🏫</span> {item.teacher}</p> : null}
                    {item.warnings.length ? <p className="friendly-warning">⚠ Please check: {item.warnings.join(" · ")}</p> : null}
                  </div>
                  <details className="source-proof source-proof-v4">
                    <summary>Check original sheet</summary>
                    <small>{item.workbook_name}</small>
                    <small>{item.sheet_name}, row {item.source_row}</small>
                    {item.source_coordinates.length ? <small>Cells: {item.source_coordinates.join(", ")}</small> : null}
                  </details>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
