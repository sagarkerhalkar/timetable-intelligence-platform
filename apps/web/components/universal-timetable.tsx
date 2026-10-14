import type { TimetableEntry } from "@/lib/types";
import { formatTime } from "@/lib/format";

const ICONS: Array<[RegExp, string]> = [
  [/account/i, "🧾"], [/business|entrepreneur/i, "💼"], [/econom/i, "📈"],
  [/math/i, "🧮"], [/physics/i, "⚛️"], [/chem/i, "🧪"], [/biology/i, "🌿"],
  [/political/i, "🗳️"], [/history/i, "🏛️"], [/geography|social science|sst/i, "🌍"],
  [/psychology/i, "🧠"], [/sociology/i, "👥"], [/english/i, "📖"],
  [/hindi/i, "🪷"], [/sanskrit/i, "🕉️"], [/science/i, "🔬"],
];

function iconFor(subject: string | null): string {
  return ICONS.find(([pattern]) => pattern.test(subject ?? ""))?.[1] ?? "🎓";
}

function batchLabel(value: string | null): string | null {
  if (!value) return null;
  return value
    .replace("Nirmaan New NCERT", "New NCERT")
    .replace("Nirmaan Old NCERT", "Old NCERT");
}

function groups(items: TimetableEntry[]): Array<[string, TimetableEntry[]]> {
  const map = new Map<string, TimetableEntry[]>();
  for (const item of items) {
    const key = item.start_time ?? "Time pending";
    map.set(key, [...(map.get(key) ?? []), item]);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, entries]) => [
      time,
      entries.sort((a, b) =>
        `${a.stream ?? ""}|${a.class_name ?? ""}|${a.subject ?? ""}`.localeCompare(
          `${b.stream ?? ""}|${b.class_name ?? ""}|${b.subject ?? ""}`
        )
      )
    ]);
}

export function UniversalTimetable({
  items,
  title = "Today at a glance"
}: {
  items: TimetableEntry[];
  title?: string;
}) {
  return (
    <section className="universal-board" aria-label={title}>
      <div className="universal-board-head">
        <div>
          <p className="eyebrow">Universal view</p>
          <h2>{title}</h2>
          <p>One row for each start time. Read left to right—no long card list.</p>
        </div>
        <div className="universal-key">
          <span><b>1</b> Time</span><span><b>2</b> Class</span><span><b>3</b> Subject</span><span><b>4</b> Lesson</span>
        </div>
      </div>
      <div className="universal-slots">
        {groups(items).map(([time, entries]) => (
          <section className="universal-slot" key={time}>
            <div className="slot-time">
              <small>Starts</small>
              <strong>{formatTime(time)}</strong>
              <span>{entries.length} class{entries.length === 1 ? "" : "es"}</span>
            </div>
            <div className="slot-classes">
              {entries.map((item) => (
                <article className="universal-class" key={item.id}>
                  <div className="universal-class-top">
                    <span className="universal-icon" aria-hidden="true">{iconFor(item.subject)}</span>
                    <div>
                      <div className="universal-pills">
                        <span>{item.stream ?? "General"}</span>
                        <span>{item.class_name ?? "Class"}</span>
                        {batchLabel(item.batch) ? <span>{batchLabel(item.batch)}</span> : null}
                      </div>
                      <h3>{item.subject ?? "Subject pending"}</h3>
                    </div>
                  </div>
                  <p className="universal-topic">{item.topic ?? "Topic not added yet"}</p>
                  {item.teacher ? <small className="universal-teacher">👩‍🏫 {item.teacher}</small> : null}
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
