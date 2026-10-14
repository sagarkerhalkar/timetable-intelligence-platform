import { confidenceLabel } from "@/lib/format";

export function ConfidenceBadge({ value }: Readonly<{ value: number }>) {
  const label = confidenceLabel(value);
  return <span className={`confidence confidence-${label.toLowerCase()}`}>{label}</span>;
}
