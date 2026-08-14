"use client";

import { Plus, Sparkles, Upload, X, Zap } from "lucide-react";
import { useState } from "react";

const actions = [
  { label: "Nieuw product", href: "/catalogus/nieuw", icon: Plus },
  { label: "AI-productconcept", href: "/catalogus/ai-assistent", icon: Sparkles },
  { label: "Orders importeren", href: "/orders#importeren", icon: Upload },
  { label: "Printplanning openen", href: "/printplanning", icon: Zap },
];

export function QuickActions() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button aria-expanded={open} className="inline-flex min-h-10 items-center gap-2 rounded-md bg-brand px-3 py-2 text-sm font-black text-slate-950" onClick={() => setOpen(true)} type="button">
        <Plus aria-hidden="true" className="h-4 w-4" />
        <span className="hidden sm:inline">Snel toevoegen</span>
      </button>
      {open ? (
        <div aria-label="Snelacties" aria-modal="true" className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 p-4 pt-24" role="dialog">
          <div className="w-full max-w-md rounded-lg border border-line bg-panel p-5 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-black">Wat wil je doen?</h2>
              <button aria-label="Sluiten" className="rounded-md border border-line p-2" onClick={() => setOpen(false)} type="button"><X aria-hidden="true" className="h-5 w-5" /></button>
            </div>
            <div className="mt-4 grid gap-2">
              {actions.map((action) => (
                <a className="flex min-h-12 items-center gap-3 rounded-md border border-line bg-panelSoft px-4 py-3 font-bold hover:border-brand" href={action.href} key={action.href}>
                  <action.icon aria-hidden="true" className="h-5 w-5 text-brand" />{action.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
