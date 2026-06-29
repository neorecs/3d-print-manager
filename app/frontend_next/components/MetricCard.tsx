type MetricCardProps = {
  label: string;
  value: string | number;
  note?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
};

const tones = {
  neutral: "border-line bg-panel",
  good: "border-emerald-400/25 bg-emerald-950/20",
  warning: "border-amber-400/25 bg-amber-950/20",
  danger: "border-red-400/25 bg-red-950/20",
};

const dots = {
  neutral: "bg-slate-400",
  good: "bg-emerald-400",
  warning: "bg-amber-400",
  danger: "bg-red-400",
};

export function MetricCard({ label, value, note, tone = "neutral" }: MetricCardProps) {
  return (
    <div className={`rounded-2xl border ${tones[tone]} p-4 shadow-card`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
        <span className={`h-2.5 w-2.5 rounded-full ${dots[tone]}`} />
      </div>
      <div className="mt-3 text-3xl font-black tracking-normal text-ink">{value}</div>
      {note ? <div className="mt-2 text-sm font-semibold text-muted">{note}</div> : null}
    </div>
  );
}
