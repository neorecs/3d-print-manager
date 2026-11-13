import type { ReactNode } from "react";

/** White card with a thin border; the basic surface for every section. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-panel shadow-card ${className}`.trim()}>{children}</div>;
}

export function CardHeader({ title, action, id }: { title: string; action?: ReactNode; id?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3">
      <h2 className="text-base font-semibold text-ink" id={id}>{title}</h2>
      {action}
    </div>
  );
}
