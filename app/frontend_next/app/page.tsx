import Link from "next/link";
import { AlertCircle, Circle, Package, RefreshCw, ShoppingBag } from "lucide-react";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { ButtonLink, Card, CardHeader } from "@/components/ui";
import { formatCurrency, formatMinutes, getDashboardData } from "@/lib/api";
import { productInventoryHref } from "@/lib/navigation";
import {
  isPrinting,
  lastMeasuredLabel,
  operationalState,
  progressLabel,
  progressValue,
  taskLabel,
} from "@/lib/printerPresentation";
import type { DashboardData } from "@/lib/types";

export const metadata = { title: "Overzicht" };

export default async function DashboardPage() {
  let data: DashboardData | null = null;
  let error: string | null = null;

  try {
    data = await getDashboardData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  const today = new Intl.DateTimeFormat("nl-NL", { weekday: "long", day: "numeric", month: "long" }).format(new Date());

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-sm font-medium capitalize text-muted">{today}</div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink md:text-[26px]">Overzicht</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <ButtonLink href="/orders#importeren">Orders ophalen</ButtonLink>
          <ButtonLink href="/catalogus/nieuw" variant="primary">Nieuw product</ButtonLink>
        </div>
      </div>
      {error || !data ? <ErrorState message={error || "Geen data beschikbaar"} title="Dashboardgegevens niet beschikbaar" /> : <DashboardContent data={data} />}
    </AppShell>
  );
}

type Tone = "red" | "amber" | "blue";
type AttentionItem = { key: string; tone: Tone; title: string; detail: string; href: string; action: string; icon: ReactNode };

const toneClasses: Record<Tone, string> = {
  red: "bg-red-50 text-red-700",
  amber: "bg-amber-50 text-amber-800",
  blue: "bg-blue-50 text-blue-700",
};

function attentionItems(data: DashboardData): AttentionItem[] {
  const items: AttentionItem[] = [];
  const problemPrinters = data.printers.filter((printer) => {
    const state = operationalState(printer).toLowerCase();
    return printer.active && ["failed", "error", "fout", "offline", "unknown", "onbekend"].some((word) => state.includes(word));
  });
  for (const printer of problemPrinters.slice(0, 3)) {
    items.push({
      key: `printer-${printer.id}`,
      tone: "red",
      title: `Printer ${printer.name} vraagt aandacht`,
      detail: lastMeasuredLabel(printer.last_seen_at),
      href: "/bambu-printers",
      action: "Controleren",
      icon: <AlertCircle aria-hidden="true" className="h-4 w-4" />,
    });
  }
  const { metrics } = data;
  if (metrics.order_new > 0) {
    items.push({
      key: "orders-new",
      tone: "amber",
      title: `${metrics.order_new} nieuwe ${metrics.order_new === 1 ? "order wacht" : "orders wachten"} op verwerking`,
      detail: "Voorraad wordt gereserveerd; alleen het tekort gaat naar de planning.",
      href: "/orders?status=nieuw",
      action: "Verwerken",
      icon: <ShoppingBag aria-hidden="true" className="h-4 w-4" />,
    });
  }
  if (metrics.low_filament > 0) {
    items.push({
      key: "filament",
      tone: "amber",
      title: `${metrics.low_filament} filamentrol${metrics.low_filament === 1 ? "" : "len"} onder minimum`,
      detail: `${(metrics.planned_filament_grams / 1000).toFixed(1).replace(".", ",")} kg gepland verbruik in open printwerk (geschat).`,
      href: "/filament",
      action: "Naar filament",
      icon: <Circle aria-hidden="true" className="h-4 w-4" />,
    });
  }
  if (metrics.low_inventory > 0) {
    items.push({
      key: "inventory",
      tone: "amber",
      title: `${metrics.low_inventory} variant${metrics.low_inventory === 1 ? "" : "en"} onder minimumvoorraad`,
      detail: "Bekijk het voorraadadvies om bij te printen.",
      href: "/voorraad",
      action: "Naar voorraad",
      icon: <Package aria-hidden="true" className="h-4 w-4" />,
    });
  }
  if ((metrics.assisted_out_of_stock ?? 0) > 0) {
    const count = metrics.assisted_out_of_stock ?? 0;
    items.push({
      key: "assisted-sold-out",
      tone: "red",
      title: `${count} handmatig geplaatste advertentie${count === 1 ? "" : "s"} zonder vrije voorraad`,
      detail: "Pas de advertentie aan of haal hem offline op het kanaal, zodat je niets verkoopt wat er niet is.",
      href: "/verkoopkanalen",
      action: "Bekijken",
      icon: <AlertCircle aria-hidden="true" className="h-4 w-4" />,
    });
  }
  if (metrics.sync_needed > 0) {
    items.push({
      key: "sync",
      tone: "blue",
      title: `${metrics.sync_needed} publicatie${metrics.sync_needed === 1 ? " moet" : "s moeten"} opnieuw naar verkoopkanalen`,
      detail: "Product gewijzigd sinds de laatste synchronisatie.",
      href: "/verkoopkanalen",
      action: "Bekijken",
      icon: <RefreshCw aria-hidden="true" className="h-4 w-4" />,
    });
  }
  return items;
}

function DashboardContent({ data }: { data: DashboardData }) {
  const items = attentionItems(data);
  const { metrics } = data;

  return (
    <div className="space-y-6">
      <Card className="px-5 py-4 sm:px-6">
        <section aria-labelledby="aandacht">
          <CardHeader id="aandacht" title="Vraagt nu je aandacht" action={<span className="text-[13px] text-muted">{items.length ? `${items.length} ${items.length === 1 ? "actie" : "acties"}` : "Niets dringends"}</span>} />
          {items.length ? (
            <ul className="mt-2">
              {items.map((item) => (
                <li className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-hover py-3 first:border-t-0" key={item.key}>
                  <span className={`flex h-8 w-8 flex-none items-center justify-center rounded-lg ${toneClasses[item.tone]}`}>{item.icon}</span>
                  <div className="min-w-0 flex-1 basis-60">
                    <div className="text-sm font-semibold text-ink">{item.title}</div>
                    <div className="text-[13px] text-muted">{item.detail}</div>
                  </div>
                  <Link className="text-sm font-semibold text-brand hover:underline" href={item.href}>{item.action}</Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">Alle orders zijn verwerkt, voorraad en filament zitten boven het minimum en alle publicaties zijn bijgewerkt.</p>
          )}
        </section>
      </Card>

      <section aria-label="Kerncijfers" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard href="/orders" label="Open orders" note={`${metrics.orders_today} vandaag binnengekomen`} value={metrics.open_orders} />
        <MetricCard href="/printplanning" label="Open printwerk" note="Geschat op basis van printtijden" value={formatMinutes(metrics.open_print_minutes)} />
        <MetricCard href="/administratie" label="Omzet deze maand" note="Bekende orderbedragen, incl. btw" value={formatCurrency(metrics.monthly_revenue)} />
        <MetricCard href="/voorraad" label="Lage voorraad" note="Varianten onder minimum" tone={metrics.low_inventory ? "danger" : "neutral"} value={metrics.low_inventory} />
      </section>

      <section aria-labelledby="printers" className="space-y-3">
        <CardHeader id="printers" title="Printers" action={<Link className="text-sm font-semibold text-brand hover:underline" href="/bambu-printers">Alle printers</Link>} />
        {data.printers.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.printers.slice(0, 6).map((printer) => {
              const progress = progressValue(printer);
              return (
                <Link className="block rounded-xl border border-line bg-panel px-5 py-4 shadow-card transition hover:border-brand/40" href="/bambu-printers" key={printer.id}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-[15px] font-semibold text-ink">{printer.name}</div>
                    <StatusBadge status={printer.printer_state || "onbekend"} />
                  </div>
                  <div className="mt-1 truncate text-[13px] text-muted">{taskLabel(printer)}</div>
                  <div aria-label={`Voortgang ${printer.name}`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={progress ?? 0} className="mt-3.5 h-1.5 overflow-hidden rounded-full bg-track" role="progressbar">
                    <div className="h-full rounded-full bg-brand" style={{ width: `${isPrinting(printer) ? progress ?? 0 : 0}%` }} />
                  </div>
                  <div className="mt-2 flex justify-between gap-2 text-[13px] tabular-nums text-muted">
                    <span>{progressLabel(printer)}</span>
                    <span>{lastMeasuredLabel(printer.last_seen_at)}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <EmptyState actionHref="/bambu-printers/beheer" actionLabel="Printer toevoegen" description="Voeg een printer toe om de status hier te zien." title="Nog geen printers" />
        )}
      </section>

      <div className="flex flex-wrap items-start gap-4">
        <Card className="min-w-0 flex-[2_1_520px] overflow-hidden">
          <section aria-labelledby="orders-open">
            <div className="px-5 pb-3 pt-4">
              <CardHeader id="orders-open" title="Orders in behandeling" action={<Link className="text-sm font-semibold text-brand hover:underline" href="/orders">Alle orders</Link>} />
            </div>
            {data.recentOrders.length ? (
              <div className="table-scroll">
                <table className="data-table data-table-responsive">
                  <thead>
                    <tr>
                      <th scope="col">Order</th>
                      <th scope="col">Kanaal</th>
                      <th scope="col">Status</th>
                      <th className="text-right" scope="col">Bedrag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recentOrders.map((order) => (
                      <tr key={order.id}>
                        <td data-label="Order"><Link className="font-semibold text-brand hover:underline" href={`/orders/${order.id}`}>{order.internal_order_number}</Link></td>
                        <td data-label="Kanaal">{order.platform || "-"}</td>
                        <td data-label="Status"><StatusBadge status={order.status} /></td>
                        <td className="text-right tabular-nums" data-label="Bedrag">{order.total_amount != null ? formatCurrency(order.total_amount) : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-5 pb-5"><EmptyState actionHref="/orders#importeren" actionLabel="Orders ophalen" description="Nieuwe orders verschijnen hier zodra ze binnenkomen." title="Geen open orders" /></div>
            )}
          </section>
        </Card>

        <Card className="min-w-0 flex-[1_1_280px] px-5 py-4">
          <section aria-labelledby="lage-voorraad">
            <CardHeader id="lage-voorraad" title="Lage voorraad" action={<Link className="text-sm font-semibold text-brand hover:underline" href="/voorraad">Voorraad</Link>} />
            {data.lowInventory.length ? (
              <ul className="mt-3.5 space-y-4">
                {data.lowInventory.map((item) => {
                  const ratio = item.minimum_stock > 0 ? Math.max(0, Math.min(1, item.free_stock / item.minimum_stock)) : 0;
                  return (
                    <li key={`${item.product_id}-${item.variant_id}`}>
                      <Link className="block" href={productInventoryHref(item.product_id)}>
                        <div className="flex justify-between gap-2 text-sm">
                          <span className="truncate font-medium text-ink">{item.label}</span>
                          <span className="tabular-nums text-muted">{item.free_stock} / {item.minimum_stock}</span>
                        </div>
                        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-track">
                          <div className={`h-full rounded-full ${ratio < 0.25 ? "bg-red-600" : "bg-amber-500"}`} style={{ width: `${Math.max(ratio * 100, 4)}%` }} />
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted">Geen varianten onder minimum.</p>
            )}
            <ButtonLink className="mt-5 w-full" href="/analyse">Voorraadadvies bekijken</ButtonLink>
          </section>
        </Card>
      </div>
      <p className="text-xs text-muted">Lage voorraad toont vrije voorraad / minimumvoorraad. Printerstatus is de laatst gemeten waarde.</p>
    </div>
  );
}
