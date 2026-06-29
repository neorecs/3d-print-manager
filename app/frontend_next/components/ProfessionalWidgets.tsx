import { ReactNode } from "react";

type StatusSummaryItem = {
  label: string;
  value: string | number;
  tone?: "green" | "blue" | "amber" | "red" | "slate";
  href?: string;
};

type BarItem = {
  label: string;
  value: number;
  note?: string;
  href?: string;
};

const toneClasses = {
  green: "bg-emerald-400",
  blue: "bg-sky-400",
  amber: "bg-amber-400",
  red: "bg-red-400",
  slate: "bg-slate-400",
};

const tonePanels = {
  green: "border-emerald-400/20 bg-emerald-400/10",
  blue: "border-sky-400/20 bg-sky-400/10",
  amber: "border-amber-400/20 bg-amber-400/10",
  red: "border-red-400/20 bg-red-400/10",
  slate: "border-slate-400/20 bg-slate-400/10",
};

export function StatusSummary({ items }: { items: StatusSummaryItem[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {items.map((item) => {
        const tone = item.tone || "slate";
        const content = (
          <>
            <div className="flex min-w-0 items-center justify-between gap-3">
              <span className="min-w-0 text-balance break-words text-sm font-bold text-slate-200">{item.label}</span>
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${toneClasses[tone]}`} />
            </div>
            <div className="mt-2 min-w-0 break-words text-2xl font-black text-ink">{item.value}</div>
          </>
        );
        const className = `block rounded-xl border px-3 py-3 transition hover:border-brand/50 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-brand/50 ${tonePanels[tone]}`;

        if (item.href) {
          return (
            <a className={className} href={item.href} key={item.label}>
              {content}
            </a>
          );
        }

        return (
          <div className={className} key={item.label}>
            {content}
          </div>
        );
      })}
    </div>
  );
}

export function BarList({ items, maxValue }: { items: BarItem[]; maxValue?: number }) {
  const max = maxValue || Math.max(...items.map((item) => item.value), 1);
  return (
    <div className="space-y-4">
      {items.map((item) => {
        const content = (
          <>
            <div className="mb-1 flex min-w-0 items-center justify-between gap-3 px-1 text-sm">
              <span className="min-w-0 break-words font-bold text-slate-200">{item.label}</span>
              <span className="shrink-0 text-right text-muted">{item.note || item.value}</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-brand" style={{ width: `${Math.min((item.value / max) * 100, 100)}%` }} />
            </div>
          </>
        );

        if (item.href) {
          return (
            <a className="block rounded-lg transition hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-brand/40" href={item.href} key={item.label}>
              {content}
            </a>
          );
        }

        return <div key={item.label}>{content}</div>;
      })}
    </div>
  );
}

export function MiniBars({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-28 items-end gap-2">
      {values.map((value, index) => (
        <div className="flex flex-1 flex-col items-center justify-end gap-2" key={`${value}-${index}`}>
          <div
            className="w-full rounded-t-lg bg-gradient-to-t from-brand to-sky-400"
            style={{ height: `${Math.max((value / max) * 100, 10)}%` }}
          />
          <span className="text-[10px] font-bold text-muted">{index + 1}</span>
        </div>
      ))}
    </div>
  );
}

export function ActivityItem({ title, text, meta, href }: { title: string; text: string; meta?: string; href?: string }) {
  const content = (
    <>
      <div className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-brand" />
      <div className="min-w-0">
        <div className="break-words font-bold text-ink">{title}</div>
        <p className="mt-1 break-words text-sm leading-6 text-muted">{text}</p>
        {meta ? <div className="mt-1 break-words text-xs font-bold uppercase text-slate-500">{meta}</div> : null}
      </div>
    </>
  );
  const className = "flex gap-3 rounded-xl border border-line bg-panelSoft/70 p-3 transition hover:border-brand/50 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-brand/50";

  if (href) {
    return (
      <a className={className} href={href}>
        {content}
      </a>
    );
  }

  return <div className={className}>{content}</div>;
}

export function SoftPanel({ children }: { children: ReactNode }) {
  return <div className="min-w-0 rounded-xl border border-line bg-panelSoft/70 p-4">{children}</div>;
}
