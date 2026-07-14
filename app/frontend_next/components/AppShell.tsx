"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { LogoutButton } from "./LogoutButton";

const navigation = [
  {
    section: "Start",
    items: [{ label: "Dashboard", href: "/", icon: "D" }],
  },
  {
    section: "Beheer",
    items: [
      { label: "Orders", href: "/orders", icon: "O" },
      { label: "Producten", href: "/catalogus", icon: "P" },
      { label: "Verkoopkanalen", href: "/verkoopkanalen", icon: "V" },
      { label: "AI assistent", href: "/catalogus/ai-assistent", icon: "A" },
    ],
  },
  {
    section: "Operatie",
    items: [
      { label: "Voorraad", href: "/voorraad", icon: "V" },
      { label: "Filament", href: "/filament", icon: "F" },
      { label: "Printers", href: "/bambu-printers", icon: "R" },
      { label: "Printwachtrij", href: "/printplanning", icon: "Q" },
      { label: "Onderhoud", href: "/bambu-printers", icon: "M" },
    ],
  },
  {
    section: "Inzicht",
    items: [
      { label: "Analyse", href: "/analyse", icon: "G" },
      { label: "Financieel", href: "/administratie", icon: "E" },
      { label: "Gebruikers", href: "/instellingen/gebruikers", icon: "U" },
      { label: "Instellingen", href: "/instellingen", icon: "S" },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-[#090f1a]/95 backdrop-blur-xl lg:block">
        <div className="border-b border-line px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-sm font-black text-slate-950 shadow-card">3D</div>
            <div>
              <div className="text-lg font-black tracking-normal">Printfarm Manager</div>
              <div className="mt-1 text-xs font-semibold text-muted">SaaS cockpit voor productie</div>
            </div>
          </div>
        </div>
        <nav className="professional-scrollbar h-[calc(100vh-96px)] space-y-6 overflow-y-auto px-4 py-5">
          {navigation.map((group) => (
            <div key={group.section}>
              <div className="px-3 text-[11px] font-black uppercase tracking-[.14em] text-muted">{group.section}</div>
              <div className="mt-2 space-y-1">
                {group.items.map((item) => {
                  const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                  return (
                    <Link
                      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition ${
                        active
                          ? "border border-brand/30 bg-brand/15 text-white shadow-card"
                          : "text-slate-300 hover:bg-white/5 hover:text-white"
                      }`}
                      href={item.href}
                      key={`${group.section}-${item.label}`}
                    >
                      <span className={`flex h-8 w-8 items-center justify-center rounded-lg text-xs font-black ${
                        active ? "bg-brand text-slate-950" : "bg-slate-800 text-slate-300"
                      }`}>
                        {item.icon}
                      </span>
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-[#070b12]/85 backdrop-blur-xl">
          <div className="flex h-16 items-center justify-between px-5 lg:px-8">
            <div>
              <div className="text-sm font-bold text-slate-200">Nieuwe Next.js cockpit</div>
              <div className="text-xs text-muted">Productie, voorraad, verkoop en printers in een beheerlaag</div>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-brand/25 bg-brand/10 px-3 py-1 text-xs font-black text-brand">
                Prototype V2
              </div>
              <LogoutButton />
            </div>
          </div>
          <div className="professional-scrollbar flex gap-2 overflow-x-auto border-t border-line px-4 py-2 lg:hidden">
            {navigation.flatMap((group) => group.items).map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-black ${
                    active ? "bg-brand text-slate-950" : "bg-panelSoft text-slate-300"
                  }`}
                  href={item.href}
                  key={`mobile-${item.label}`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </header>
        <main className="px-4 py-6 sm:px-5 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
