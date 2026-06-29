type MetricCardProps = {
  label: string;
  value: string | number;
  note?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
  href?: string;
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

export function MetricCard({ label, value, note, tone = "neutral", href }: MetricCardProps) {
  const content = (
    <>
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0 text-balance break-words text-[11px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dots[tone]}`} />
      </div>
      <div className="mt-3 min-w-0 break-words text-2xl font-black tracking-normal text-ink sm:text-3xl">{value}</div>
      {note ? <div className="mt-2 min-w-0 text-balance break-words text-sm font-semibold text-muted">{note}</div> : null}
    </>
  );

  const className = `block h-full rounded-2xl border ${tones[tone]} p-4 shadow-card transition hover:-translate-y-0.5 hover:border-brand/50 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-brand/50`;

  if (href) {
    return (
      <a aria-label={`Ga naar ${label}`} className={className} href={href}>
        {content}
      </a>
    );
  }

  return <div className={className}>{content}</div>;
}
