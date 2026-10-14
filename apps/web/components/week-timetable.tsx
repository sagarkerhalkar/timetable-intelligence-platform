"use client";

import { useEffect, useMemo, useState } from "react";
import type { TimetableEntry } from "@/lib/types";
import { formatShortDate, formatTime, indiaDateISO } from "@/lib/format";

function subjectIcon(subject: string | null): string {
  const value = (subject ?? "").toLowerCase();
  if (value.includes("math")) return "➗";
  if (value.includes("physics")) return "⚛️";
  if (value.includes("chem")) return "🧪";
  if (value.includes("bio")) return "🧬";
  if (value.includes("account")) return "🧾";
  if (value.includes("econom")) return "📈";
  if (value.includes("business")) return "💼";
  if (value.includes("history")) return "🏛️";
  if (value.includes("geography")) return "🌍";
  if (value.includes("political")) return "🗳️";
  if (value.includes("english")) return "🔤";
  if (value.includes("hindi")) return "हिं";
  if (value.includes("sanskrit")) return "सं";
  if (value.includes("science")) return "🔬";
  return "📘";
}

function groupByTime(items: TimetableEntry[]): Array<[string, TimetableEntry[]]> {
  const groups = new Map<string, TimetableEntry[]>();
  for (const item of items) {
    const key = item.start_time ?? "99:99";
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export function WeekTimetable({ items, dates }: Readonly<{ items: TimetableEntry[]; dates: string[] }>) {
  const streams = useMemo(
    () => ["All", ...Array.from(new Set(items.map((item) => item.stream).filter((value): value is string => Boolean(value)))).sort()],
    [items]
  );
  const today = indiaDateISO();
  const firstDateWithClass = dates.find((date) => items.some((item) => item.class_date === date));
  const initialDate = items.some((item) => item.class_date === today)
    ? today
    : (firstDateWithClass ?? dates[0] ?? today);
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [stream, setStream] = useState("All");

  const filtered = useMemo(
    () => items.filter((item) => stream === "All" || item.stream === stream),
    [items, stream]
  );
  const dayItems = useMemo(
    () => filtered.filter((item) => item.class_date === selectedDate),
    [filtered, selectedDate]
  );
  const timeGroups = useMemo(() => groupByTime(dayItems), [dayItems]);

  useEffect(() => {
    if (dayItems.length) return;
    const nextDate = dates.find((date) =>
      filtered.some((item) => item.class_date === date)
    );
    if (nextDate && nextDate !== selectedDate) setSelectedDate(nextDate);
  }, [dates, dayItems.length, filtered, selectedDate]);

  return (
    <section className="week-v1" aria-label="Simple weekly timetable">
      <header className="week-v1-header">
        <div>
          <p className="eyebrow">One week at a glance</p>
          <h2>Choose a day, then see its classes</h2>
          <p>All seven days stay visible. Details open only for the selected day, so the page stays short and clear.</p>
        </div>
        <div className="week-v1-total"><strong>{filtered.length}</strong><span>classes</span></div>
      </header>

      <div className="week-stream-switch" aria-label="Filter weekly timetable by stream">
        {streams.map((value) => (
          <button key={value} className={stream === value ? "active" : ""} type="button" onClick={() => setStream(value)}>
            {value === "All" ? "All streams" : value}
          </button>
        ))}
      </div>

      <div className="week-day-strip" role="tablist" aria-label="Days of this week">
        {dates.map((date) => {
          const entries = filtered.filter((item) => item.class_date === date);
          const subjects = Array.from(new Set(entries.map((item) => item.subject).filter(Boolean))).slice(0, 3);
          return (
            <button
              key={date}
              type="button"
              role="tab"
              aria-selected={selectedDate === date}
              className={`${selectedDate === date ? "active" : ""} ${date === today ? "today" : ""}`}
              onClick={() => setSelectedDate(date)}
            >
              <span>{formatShortDate(date)}</span>
              <strong>{entries.length}</strong>
              <small>{entries.length ? subjects.join(" · ") : "No class"}</small>
            </button>
          );
        })}
      </div>

      <section className="week-day-focus" role="tabpanel">
        <div className="week-focus-title">
          <div><p className="eyebrow">Selected day</p><h3>{formatShortDate(selectedDate)}</h3></div>
          <span>{dayItems.length} class{dayItems.length === 1 ? "" : "es"}</span>
        </div>
        {timeGroups.length ? (
          <div className="week-time-list">
            {timeGroups.map(([time, entries]) => (
              <div className="week-time-row" key={time}>
                <div className="week-time-label"><strong>{formatTime(time)}</strong><small>{entries.length} at this time</small></div>
                <div className="week-time-classes">
                  {entries.map((item) => (
                    <article key={item.id}>
                      <span className="week-subject-icon" aria-hidden="true">{subjectIcon(item.subject)}</span>
                      <div>
                        <small>{item.stream ?? "General"} · {item.class_name ?? "Class"}{item.batch ? ` · ${item.batch}` : ""}</small>
                        <strong>{item.subject ?? "Subject pending"}</strong>
                        <p>{item.topic ?? "Topic not added"}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : <div className="week-no-class"><span>🌤️</span><strong>No class on this day</strong><p>Choose another day above.</p></div>}
      </section>
    </section>
  );
}
