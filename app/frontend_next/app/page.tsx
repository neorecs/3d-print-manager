import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { ActivityItem, BarList, MiniBars, SoftPanel, StatusSummary } from "@/components/ProfessionalWidgets";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getDashboardData } from "@/lib/api";
import { printJobHref, productInventoryHref } from "@/lib/navigation";
import type { DashboardData } from "@/lib/types";

export default async function DashboardPage() {
  let data: DashboardData | null = null;
  let error: string | null = null;

  try {
    data = await getDashboardData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Printfarm dashboard"
        description="Realtime overzicht voor printers, orders, voorraad, filament en productieplanning."
        actions={<a className="rounded-xl bg-brand px-4 py-2 text-sm font-black text-slate-950" href="/">Ververs dashboard</a>}
      />
      {error || !data ? <DashboardError message={error || "Geen data beschikbaar"} /> : <DashboardContent data={data} />}
    </AppShell>
  );
}

function DashboardError({ message }: { message: string }) {
  return <ErrorState message={message} title="Dashboardgegevens niet beschikbaar" />;
}

function DashboardContent({ data }: { data: DashboardData }) {
  const productBars = data.topProducts.map((item) => ({
    label: item.label,
    value: item.sold,
    note: `${item.sold} verkocht`,
    href: `/catalogus/${item.product_id}`,
  }));
  const inventoryBars = data.lowInventory.map((item) => ({
    label: item.label,
    value: Math.max(item.minimum_stock - item.free_stock, 1),
    note: `${item.free_stock} vrij`,
    href: productInventoryHref(item.product_id),
  }));
  const printerState = (printer: DashboardData["printers"][number]) => (printer.printer_state || "offline").toLowerCase();
  const onlinePrinters = data.printers.filter((printer) => printer.active && !["offline", "unknown", "onbekend"].includes(printerState(printer)));
  const printingPrinters = data.printers.filter((printer) => ["running", "printing", "print", "bezig"].includes(printerState(printer)));
  const pausedPrinters = data.printers.filter((printer) => printerState(printer).includes("pause"));
  const errorPrinters = data.printers.filter((printer) => ["failed", "error", "fout"].some((state) => printerState(printer).includes(state)));
  const offlinePrinters = data.printers.filter((printer) => !printer.active || ["offline", "unknown", "onbekend"].includes(printerState(printer)));
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard href="/bambu-printers" label="Actieve printers" value={onlinePrinters.length} note={`${data.printers.length} geregistreerd`} tone="good" />
        <MetricCard href="/printplanning" label="Prints bezig" value={printingPrinters.length} note={formatMinutes(data.metrics.open_print_minutes)} tone="warning" />
        <MetricCard href="/orders" label="Orders vandaag" value={data.metrics.orders_today} note="nieuw binnengekomen" />
        <MetricCard href="/orders" label="Openstaande orders" value={data.metrics.open_orders} note="nog te verwerken" tone="warning" />
        <MetricCard href="/voorraad" label="Voorraadwaarde" value={formatCurrency(data.metrics.inventory_value)} note="indicatieve waarde" />
        <MetricCard href="/administratie" label="Omzet maand" value={formatCurrency(data.metrics.monthly_revenue)} note="verwacht / bekend" tone="good" />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard title="Printerstatus" description="Farmstatus op basis van printer- en printwachtrijsignalen.">
          <StatusSummary
            items={[
              { label: "Online", value: onlinePrinters.length, tone: "green", href: "/bambu-printers" },
              { label: "Print bezig", value: printingPrinters.length, tone: "blue", href: "/printplanning" },
              { label: "Pauze", value: pausedPrinters.length, tone: "slate", href: "/bambu-printers" },
              { label: "Foutmelding", value: errorPrinters.length, tone: "red", href: "/bambu-printers" },
              { label: "Offline", value: offlinePrinters.length, tone: "amber", href: "/bambu-printers" },
            ]}
          />
        </SectionCard>
        <SectionCard title="Orderstatus" description="Werkvoorraad van verkoop naar productie.">
          <StatusSummary
            items={[
              { label: "Nieuw", value: data.metrics.order_new, tone: "amber", href: "/orders?status=nieuw" },
              { label: "In productie", value: data.metrics.order_production, tone: "blue", href: "/orders?status=in-productie" },
              { label: "Klaar", value: data.metrics.order_packed, tone: "green", href: "/orders?status=klaar" },
              { label: "Verzonden", value: data.metrics.order_shipped, tone: "green", href: "/orders?status=verzonden" },
              { label: "Geannuleerd", value: data.metrics.order_cancelled, tone: "red", href: "/orders?status=geannuleerd" },
            ]}
          />
        </SectionCard>
        <SectionCard title="Filamentstatus" description="Materiaalrisico voor de komende prints.">
          <StatusSummary
            items={[
              { label: "Rollen op voorraad", value: data.metrics.filament_rolls, tone: "green", href: "/filament" },
              { label: "Bijna leeg", value: data.metrics.low_filament, tone: data.metrics.low_filament ? "amber" : "green", href: "/filament" },
              { label: "Onder minimum", value: data.metrics.low_filament, tone: data.metrics.low_filament ? "red" : "green", href: "/filament" },
              { label: "Gepland verbruik", value: `${(data.metrics.planned_filament_grams / 1000).toFixed(1)} kg`, tone: "blue", href: "/analyse" },
              { label: "Kleuren actief", value: data.metrics.active_filament_colors, tone: "slate", href: "/filament" },
            ]}
          />
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <SectionCard title="Printer live overzicht" description="Laatst ontvangen status van de geregistreerde Bambu-printers.">
          <div className="grid gap-4 md:grid-cols-2">
            {data.printers.map((printer) => (
              <a className="block rounded-xl focus:outline-none focus:ring-2 focus:ring-brand/50" href="/bambu-printers" key={printer.id}>
              <SoftPanel>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="break-words text-lg font-black text-ink">{printer.name}</div>
                    <div className="mt-1 break-words text-sm text-muted">{printer.current_task || "Geen actieve opdracht"}</div>
                  </div>
                  <StatusBadge status={printer.printer_state || "onbekend"} />
                </div>
                <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${Math.max(0, Math.min(100, Number(printer.print_progress || 0)))}%` }} />
                </div>
                <div className="mt-3 flex flex-wrap justify-between gap-2 text-sm text-muted">
                  <span>{Math.round(Number(printer.print_progress || 0))}%</span>
                  <span>Nozzle {Math.round(Number(printer.nozzle_temperature || 0))}C / Bed {Math.round(Number(printer.bed_temperature || 0))}C</span>
                </div>
              </SoftPanel>
              </a>
            ))}
            {!data.printers.length ? <EmptyState title="Geen printers" description="Voeg een printer toe om live status te tonen." /> : null}
          </div>
        </SectionCard>
        <SectionCard title="Omzettrend" description="Werkelijke orderomzet per maand in het huidige jaar.">
          {data.monthlyRevenue.some((value) => value > 0) ? <MiniBars values={data.monthlyRevenue} /> : <EmptyState title="Nog geen omzet" description="De omzetgrafiek verschijnt zodra orders met een bedrag zijn geïmporteerd." actionHref="/orders" actionLabel="Naar orders" />}
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-4">
        <SectionCard title="Best verkochte producten" description="Voorraad en productie richten op hardlopers.">
          {productBars.length ? <BarList items={productBars} /> : <EmptyState title="Geen productdata" description="Maak producten aan om dit overzicht te vullen." />}
        </SectionCard>
        <SectionCard title="Lage voorraad" description="Productvarianten onder of rond minimumvoorraad.">
          {inventoryBars.length ? <BarList items={inventoryBars} /> : <EmptyState title="Voorraad rustig" description="Geen productvoorraad onder minimum." />}
        </SectionCard>
        <SectionCard title="Geplande prints" description="Open printtaken voor de komende productie.">
          <div className="space-y-3">
            {data.openPrintJobs.map((job) => (
              <ActivityItem href={printJobHref(job.id)} key={job.id} title={`Printtaak #${job.id}`} text={`${job.quantity_planned || job.quantity_needed} stuks in ${job.material || "-"} / ${job.color || "-"}`} meta={job.status || "nieuw"} />
            ))}
            {!data.openPrintJobs.length ? <EmptyState title="Geen planning" description="Open printtaken verschijnen hier." /> : null}
          </div>
        </SectionCard>
        <SectionCard title="Recente waarschuwingen" description="Snelle signalen die aandacht nodig hebben.">
          <div className="space-y-3">
            <ActivityItem href="/verkoopkanalen" title="Synchronisatie" text={`${data.metrics.sync_needed} publicatie(s) moeten opnieuw naar verkoopkanalen.`} meta="verkoopkanalen" />
            <ActivityItem href="/filament" title="Filament" text={`${data.metrics.low_filament} rol(len) zitten rond of onder minimum.`} meta="voorraad" />
            <ActivityItem href="/voorraad" title="Productvoorraad" text={`${data.metrics.low_inventory} variant(en) hebben lage vrije voorraad.`} meta="planning" />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
