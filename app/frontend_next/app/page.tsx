import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { ActivityItem, BarList, MiniBars, SoftPanel, StatusSummary } from "@/components/ProfessionalWidgets";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getDashboardData } from "@/lib/api";
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
  const openOrders = data.orders.filter((order) => !["verzonden", "geannuleerd", "afgerond"].includes(order.status || ""));
  const todayOrders = data.orders.filter((order) => {
    if (!order.order_date) return false;
    return new Date(order.order_date).toDateString() === new Date().toDateString();
  });
  const openPrintJobs = data.printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const lowInventory = data.inventory.filter((item) => item.quantity_on_hand - item.quantity_reserved <= item.minimum_stock_level);
  const lowFilament = data.filament.filter((item) => item.active && item.remaining_weight_grams <= item.minimum_remaining_grams);
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig");
  const now = new Date();
  const monthOrders = data.orders.filter((order) => {
    if (!order.order_date) return false;
    const orderDate = new Date(order.order_date);
    return orderDate.getFullYear() === now.getFullYear() && orderDate.getMonth() === now.getMonth();
  });
  const revenue = monthOrders.reduce((total, order) => total + Number(order.total_amount || 0), 0);
  const variantById = new Map(data.variants.map((variant) => [variant.id, variant]));
  const inventoryValue = data.inventory.reduce(
    (total, item) => total + Math.max(item.quantity_on_hand - item.quantity_reserved, 0) * Number(variantById.get(item.product_variant_id)?.cost_price || 0),
    0,
  );
  const estimatedPrintMinutes = openPrintJobs.reduce(
    (total, job) => total + Number(job.estimated_print_time_minutes || 0),
    0,
  );
  const soldByProduct = new Map<number, number>();
  data.orderItems.forEach((item) => {
    if (item.product_id) soldByProduct.set(item.product_id, (soldByProduct.get(item.product_id) || 0) + Number(item.quantity_ordered || 0));
  });
  const productBars = data.products
    .map((product) => ({
      label: product.internal_title || product.name,
      value: soldByProduct.get(product.id) || 0,
      note: `${soldByProduct.get(product.id) || 0} verkocht`,
      href: `/catalogus/${product.id}`,
    }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);
  const inventoryBars = lowInventory.slice(0, 5).map((item) => ({
    label: `Variant ${item.product_variant_id}`,
    value: Math.max(item.minimum_stock_level - (item.quantity_on_hand - item.quantity_reserved), 1),
    note: `${item.quantity_on_hand - item.quantity_reserved} vrij`,
    href: "/voorraad",
  }));
  const printerState = (printer: DashboardData["printers"][number]) => (printer.printer_state || "offline").toLowerCase();
  const onlinePrinters = data.printers.filter((printer) => printer.active && !["offline", "unknown", "onbekend"].includes(printerState(printer)));
  const printingPrinters = data.printers.filter((printer) => ["running", "printing", "print", "bezig"].includes(printerState(printer)));
  const pausedPrinters = data.printers.filter((printer) => printerState(printer).includes("pause"));
  const errorPrinters = data.printers.filter((printer) => ["failed", "error", "fout"].some((state) => printerState(printer).includes(state)));
  const offlinePrinters = data.printers.filter((printer) => !printer.active || ["offline", "unknown", "onbekend"].includes(printerState(printer)));
  const monthlyRevenue = Array.from({ length: 12 }, (_, month) =>
    data.orders
      .filter((order) => {
        if (!order.order_date) return false;
        const orderDate = new Date(order.order_date);
        return orderDate.getFullYear() === now.getFullYear() && orderDate.getMonth() === month;
      })
      .reduce((total, order) => total + Number(order.total_amount || 0), 0),
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard href="/bambu-printers" label="Actieve printers" value={onlinePrinters.length} note={`${data.printers.length} geregistreerd`} tone="good" />
        <MetricCard href="/printplanning" label="Prints bezig" value={printingPrinters.length} note={formatMinutes(estimatedPrintMinutes)} tone="warning" />
        <MetricCard href="/orders" label="Orders vandaag" value={todayOrders.length} note="nieuw binnengekomen" />
        <MetricCard href="/orders" label="Openstaande orders" value={openOrders.length} note="nog te verwerken" tone="warning" />
        <MetricCard href="/voorraad" label="Voorraadwaarde" value={formatCurrency(inventoryValue)} note="indicatieve waarde" />
        <MetricCard href="/administratie" label="Omzet maand" value={formatCurrency(revenue)} note="verwacht / bekend" tone="good" />
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
              { label: "Nieuw", value: data.orders.filter((o) => o.status === "nieuw").length, tone: "amber", href: "/orders" },
              { label: "In productie", value: data.orders.filter((o) => (o.status || "").includes("print")).length, tone: "blue", href: "/orders" },
              { label: "Klaar", value: data.orders.filter((o) => o.status === "ingepakt").length, tone: "green", href: "/orders" },
              { label: "Verzonden", value: data.orders.filter((o) => o.status === "verzonden").length, tone: "green", href: "/orders" },
              { label: "Geannuleerd", value: data.orders.filter((o) => o.status === "geannuleerd").length, tone: "red", href: "/orders" },
            ]}
          />
        </SectionCard>
        <SectionCard title="Filamentstatus" description="Materiaalrisico voor de komende prints.">
          <StatusSummary
            items={[
              { label: "Rollen op voorraad", value: data.filament.length, tone: "green", href: "/filament" },
              { label: "Bijna leeg", value: lowFilament.length, tone: lowFilament.length ? "amber" : "green", href: "/filament" },
              { label: "Onder minimum", value: lowFilament.length, tone: lowFilament.length ? "red" : "green", href: "/filament" },
              { label: "Gepland verbruik", value: `${(openPrintJobs.reduce((total, job) => total + Number(job.estimated_filament_grams || 0), 0) / 1000).toFixed(1)} kg`, tone: "blue", href: "/analyse" },
              { label: "Kleuren actief", value: new Set(data.filament.map((item) => item.color)).size, tone: "slate", href: "/filament" },
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
          {monthlyRevenue.some((value) => value > 0) ? <MiniBars values={monthlyRevenue} /> : <EmptyState title="Nog geen omzet" description="De omzetgrafiek verschijnt zodra orders met een bedrag zijn geïmporteerd." actionHref="/orders" actionLabel="Naar orders" />}
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
            {openPrintJobs.slice(0, 5).map((job) => (
              <ActivityItem href="/printplanning" key={job.id} title={`Printtaak #${job.id}`} text={`${job.quantity_planned || job.quantity_needed} stuks in ${job.material || "-"} / ${job.color || "-"}`} meta={job.status || "nieuw"} />
            ))}
            {!openPrintJobs.length ? <EmptyState title="Geen planning" description="Open printtaken verschijnen hier." /> : null}
          </div>
        </SectionCard>
        <SectionCard title="Recente waarschuwingen" description="Snelle signalen die aandacht nodig hebben.">
          <div className="space-y-3">
            <ActivityItem href="/verkoopkanalen" title="Synchronisatie" text={`${syncNeeded.length} publicatie(s) moeten opnieuw naar verkoopkanalen.`} meta="verkoopkanalen" />
            <ActivityItem href="/filament" title="Filament" text={`${lowFilament.length} rol(len) zitten rond of onder minimum.`} meta="voorraad" />
            <ActivityItem href="/voorraad" title="Productvoorraad" text={`${lowInventory.length} variant(en) hebben lage vrije voorraad.`} meta="planning" />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
