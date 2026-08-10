export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Not checked yet";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata"
  }).format(parsed);
}

export function formatTime(value: string | null): string {
  if (!value) return "Time pending";
  const [hourRaw, minuteRaw] = value.split(":");
  const hour = Number(hourRaw);
  const minute = Number(minuteRaw);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return value;
  const suffix = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${String(minute).padStart(2, "0")} ${suffix}`;
}

export function indiaDateISO(offsetDays = 0): string {
  const now = new Date();
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(now);
  const year = Number(parts.find((part) => part.type === "year")?.value);
  const month = Number(parts.find((part) => part.type === "month")?.value);
  const day = Number(parts.find((part) => part.type === "day")?.value);
  const date = new Date(Date.UTC(year, month - 1, day + offsetDays));
  return date.toISOString().slice(0, 10);
}

export function formatFullDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00+05:30`);
  if (Number.isNaN(parsed.valueOf())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Kolkata"
  }).format(parsed);
}

export function formatShortDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00+05:30`);
  if (Number.isNaN(parsed.valueOf())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata"
  }).format(parsed);
}

export function confidenceLabel(value: number): "High" | "Review" | "Low" {
  if (value >= 0.8) return "High";
  if (value >= 0.55) return "Review";
  return "Low";
}

function parseCivilDateUtc(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null;
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) return null;
  return parsed;
}

export function indiaWeekDates(anchor = indiaDateISO()): string[] {
  const parsed = parseCivilDateUtc(anchor);
  if (!parsed) return [];
  const day = parsed.getUTCDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(parsed);
  monday.setUTCDate(monday.getUTCDate() + mondayOffset);
  return Array.from({ length: 7 }, (_, index) => {
    const current = new Date(monday);
    current.setUTCDate(monday.getUTCDate() + index);
    return current.toISOString().slice(0, 10);
  });
}
