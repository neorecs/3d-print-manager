import Link from "next/link";
type MetricCardProps = {
  label: string;
  value: string | number;
  note?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
  href?: string;
};

const tones = {
  neutral: "border-line bg-panel",
  good: "border-line bg-panel",
  warning: "border-line bg-panel",
  danger: "border-red-200 bg-panel",
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
        <div className="min-w-0 text-balance break-words text-[13px] font-medium text-muted">{label}</div>
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dots[tone]}`} />
      </div>
      <div className="mt-1.5 min-w-0 break-words text-2xl font-semibold tracking-tight text-ink tabular-nums sm:text-[28px]">{value}</div>
      {note ? <div className="mt-1 min-w-0 text-balance break-words text-[13px] text-muted">{note}</div> : null}
    </>
  );

  const className = `block h-full rounded-xl border ${tones[tone]} px-5 py-4 shadow-card transition hover:border-brand/40 focus:outline-none focus:ring-2 focus:ring-brand/50`;

  if (href) {
    return (
      <Link aria-label={`Ga naar ${label}`} className={className} href={href}>
        {content}
      </Link>
    );
  }

  return <div className={className}>{content}</div>;
}
