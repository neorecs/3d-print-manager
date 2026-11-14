"use client";

import {
  BarChart3,
  Boxes,
  ChevronDown,
  CircleDollarSign,
  Factory,
  Gauge,
  Layers3,
  PackageSearch,
  Printer,
  Search,
  Settings,
  ShoppingBag,
  Store,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { GlobalSearch } from "./GlobalSearch";
import { LogoutButton } from "./LogoutButton";
import { QuickActions } from "./QuickActions";

type NavigationItem = { label: string; href: string; icon: LucideIcon };

const navigation: Array<{ section: string; items: NavigationItem[] }> = [
  { section: "Start", items: [{ label: "Dashboard", href: "/", icon: Gauge }] },
  {
    section: "Dagelijks werk",
    items: [
      { label: "Orders", href: "/orders", icon: ShoppingBag },
      { label: "Producten", href: "/catalogus", icon: PackageSearch },
      { label: "Productie", href: "/printplanning", icon: Factory },
      { label: "Voorraad", href: "/voorraad", icon: Boxes },
      { label: "Filament", href: "/filament", icon: Layers3 },
      { label: "Printers", href: "/bambu-printers", icon: Printer },
    ],
  },
  {
    section: "Inzicht",
    items: [
      { label: "Analyse", href: "/analyse", icon: BarChart3 },
      { label: "Administratie", href: "/administratie", icon: CircleDollarSign },
      { label: "Verkoopkanalen", href: "/verkoopkanalen", icon: Store },
    ],
  },
];

const mobilePrimary: NavigationItem[] = [
  { label: "Dashboard", href: "/", icon: Gauge },
  { label: "Orders", href: "/orders", icon: ShoppingBag },
  { label: "Producten", href: "/catalogus", icon: PackageSearch },
  { label: "Productie", href: "/printplanning", icon: Factory },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function NavigationLink({ item, pathname }: { item: NavigationItem; pathname: string }) {
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <Link
      aria-current={active ? "page" : undefined}
      className={`flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
        active ? "bg-brandSoft font-semibold text-brand" : "font-medium text-inkSoft hover:bg-hover hover:text-ink"
      }`}
      href={item.href}
    >
      <Icon aria-hidden="true" className={`h-[18px] w-[18px] ${active ? "text-brand" : "text-muted"}`} />
      {item.label}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas pb-20 text-ink lg:pb-0">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-panel lg:block">
        <div className="border-b border-line px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand text-onBrand">
              <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" /><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5" /></svg>
            </div>
            <div>
              <div className="text-[15px] font-semibold leading-tight">3D Print Manager</div>
              <div className="text-xs text-muted">Productie &amp; verkoop</div>
            </div>
          </div>
        </div>
        <nav aria-label="Hoofdnavigatie" className="professional-scrollbar h-[calc(100vh-168px)] space-y-6 overflow-y-auto px-4 py-5">
          {navigation.map((group) => (
            <div key={group.section}>
              <div className="px-3 text-xs font-medium text-muted">{group.section}</div>
              <div className="mt-2 space-y-1">
                {group.items.map((item) => <NavigationLink item={item} key={item.href} pathname={pathname} />)}
              </div>
            </div>
          ))}
        </nav>
        <div className="absolute inset-x-0 bottom-0 border-t border-line bg-panel p-4">
          <NavigationLink item={{ label: "Instellingen", href: "/instellingen", icon: Settings }} pathname={pathname} />
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-canvas/95 backdrop-blur">
          <div className="flex min-h-16 items-center gap-3 px-4 py-3 sm:px-5 lg:px-8">
            <div className="min-w-0 md:hidden">
              <div className="text-sm font-semibold text-ink">3D Print Manager</div>
              <div className="text-xs text-muted">Alleen lokaal netwerk</div>
            </div>
            <GlobalSearch />
            <div className="ml-auto flex shrink-0 items-center gap-2">
              <QuickActions />
              <details className="relative hidden sm:block">
                <summary className="flex min-h-10 cursor-pointer list-none items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink">
                  Beheer <ChevronDown aria-hidden="true" className="h-4 w-4" />
                </summary>
                <div className="absolute right-0 mt-2 w-56 rounded-md border border-line bg-panel p-2 shadow-card">
                  <Link className="block rounded-md px-3 py-2 text-sm font-medium hover:bg-hover" href="/account/beveiliging">Account en beveiliging</Link>
                  <Link className="block rounded-md px-3 py-2 text-sm font-medium hover:bg-hover" href="/instellingen/gebruikers">Gebruikers beheren</Link>
                  <Link className="block rounded-md px-3 py-2 text-sm font-medium hover:bg-hover" href="/instellingen">Systeeminstellingen</Link>
                </div>
              </details>
              <LogoutButton />
            </div>
          </div>
          <details className="group border-t border-line lg:hidden" key={`mobile-menu-${pathname}`}>
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-4 py-2 text-sm font-semibold text-ink">
              Meer onderdelen <ChevronDown aria-hidden="true" className="h-4 w-4 text-brand transition group-open:rotate-180" />
            </summary>
            <nav aria-label="Overige navigatie" className="grid max-h-[60vh] grid-cols-2 gap-2 overflow-y-auto border-t border-line bg-panel p-3">
              {[...navigation.flatMap((group) => group.items).filter((item) => !mobilePrimary.some((primary) => primary.href === item.href)),
                { label: "Zoeken", href: "/zoeken", icon: Search },
                { label: "Instellingen", href: "/instellingen", icon: Settings }].map((item) => (
                <NavigationLink item={item} key={`mobile-more-${item.href}`} pathname={pathname} />
              ))}
            </nav>
          </details>
        </header>
        <main className="px-4 py-6 sm:px-5 lg:px-8">{children}</main>
      </div>

      <nav aria-label="Mobiele hoofdnavigatie" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-line bg-panel px-1 py-1 lg:hidden">
        {mobilePrimary.map((item) => {
          const Icon = item.icon;
          const active = isActive(pathname, item.href);
          return (
            <Link aria-current={active ? "page" : undefined} className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-md text-[11px] font-semibold ${active ? "text-brand" : "text-muted"}`} href={item.href} key={`mobile-primary-${item.href}`}>
              <Icon aria-hidden="true" className="h-5 w-5" />{item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
