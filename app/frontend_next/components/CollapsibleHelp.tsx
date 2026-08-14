import { CircleHelp } from "lucide-react";
import { ReactNode } from "react";

export function CollapsibleHelp({ title = "Wat kan ik hier doen?", children }: { title?: string; children: ReactNode }) {
  return (
    <details className="rounded-md border border-line bg-panelSoft px-4 py-3">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-black text-slate-200">
        <CircleHelp aria-hidden="true" className="h-4 w-4 text-brand" />{title}
      </summary>
      <div className="mt-3 text-sm leading-6 text-muted">{children}</div>
    </details>
  );
}
