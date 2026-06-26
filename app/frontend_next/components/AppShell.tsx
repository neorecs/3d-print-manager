import Link from "next/link";
import { ReactNode } from "react";

const navigation = [
  {
    section: "Start",
    items: [{ label: "Dashboard", href: "/" }],
  },
  {
    section: "Beheer",
    items: [
      { label: "Catalogus", href: "/catalogus" },
      { label: "AI assistent", href: "/catalogus/ai-assistent" },
      { label: "Verkoopkanalen", href: "/verkoopkanalen" },
      { label: "Orders", href: "/orders" },
    ],
  },
  {
    section: "Operatie",
    items: [
      { label: "Voorraad", href: "/voorraad" },
      { label: "Filament", href: "/filament" },
      { label: "Printplanning", href: "/printplanning" },
      { label: "Bambu printers", href: "/bambu-printers" },
    ],
  },
  {
    section: "Inzicht",
    items: [
      { label: "Analyse", href: "/analyse" },
      { label: "Instellingen", href: "/instellingen" },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-line bg-white lg:block">
        <div className="border-b border-line px-6 py-5">
          <div className="text-lg font-bold">3D Print Manager</div>
          <div className="mt-1 text-sm text-muted">Productie & verkoopbeheer</div>
        </div>
        <nav className="space-y-5 px-4 py-5">
          {navigation.map((group) => (
            <div key={group.section}>
              <div className="px-3 text-xs font-bold uppercase tracking-wide text-muted">{group.section}</div>
              <div className="mt-2 space-y-1">
                {group.items.map((item) => (
                  <Link
                    className="block rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    href={item.href}
                    key={item.href}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-5 lg:px-8">
            <div>
              <div className="text-sm font-semibold text-muted">Nieuwe Next.js frontend</div>
              <div className="text-xs text-muted">Streamlit blijft tijdelijk beschikbaar als fallback</div>
            </div>
            <div className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              Prototype V2
            </div>
          </div>
        </header>
        <main className="px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
