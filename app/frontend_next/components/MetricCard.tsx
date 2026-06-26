type MetricCardProps = {
  label: string;
  value: string | number;
  note?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
};

const tones = {
  neutral: "border-line",
  good: "border-emerald-200",
  warning: "border-amber-200",
  danger: "border-red-200",
};

export function MetricCard({ label, value, note, tone = "neutral" }: MetricCardProps) {
  return (
    <div className={`rounded-lg border ${tones[tone]} bg-white p-4 shadow-card`}>
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-3 text-3xl font-bold text-ink">{value}</div>
      {note ? <div className="mt-2 text-sm text-muted">{note}</div> : null}
    </div>
  );
}
