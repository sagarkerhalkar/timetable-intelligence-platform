import { formatNumber } from "@/lib/format";

export function StatCard({
  label,
  value,
  detail,
  icon,
  tone = "blue"
}: Readonly<{
  label: string;
  value: number;
  detail: string;
  icon: string;
  tone?: "blue" | "cyan" | "violet" | "amber";
}>) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <div className="stat-icon" aria-hidden="true">{icon}</div>
      <p>{label}</p>
      <strong>{formatNumber(value)}</strong>
      <small>{detail}</small>
    </article>
  );
}
