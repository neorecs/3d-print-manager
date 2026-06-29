import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { ActivityItem, BarList, MiniBars, SoftPanel, StatusSummary } from "@/components/ProfessionalWidgets";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getDashboardData } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

const printerMock = [
  { name: "X1C Farm 01", status: "print bezig", progress: 68, task: "Dumpling Rood batch", tone: "blue" as const },
  { name: "P1S Farm 02", status: "beschikbaar", progress: 0, task: "Wacht op batch", tone: "green" as const },
  { name: "A1 Mini 03", status: "aandacht nodig", progress: 34, task: "Keychain set", tone: "amber" as const },
  { name: "P1P 04", status: "offline", progress: 0, task: "Geen verbinding", tone: "slate" as const },
];

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
  return (
    <SectionCard title="Backend niet bereikbaar" description="De visuele basis blijft beschikbaar, maar live data kon niet worden geladen.">
      <EmptyState title="Nog geen dashboarddata" description={`Details: ${message}`} />
    </SectionCard>
  );
}

function DashboardContent({ data }: { data: DashboardData }) {
  const openOrders = data.orders.filter((order) => !["verzonden", "geannuleerd", "afgerond"].includes(order.status || ""));
  const todayOrders = data.orders.filter((order) => {
    if (!order.order_date) return false;
    return new Date(order.order_date).toDateString() === new Date().toDateString();
  });
  const openPrintJobs = data.printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const printingJobs = openPrintJobs.filter((job) => ["bezig", "gepland", "nieuw"].includes(job.status || ""));
  const lowInventory = data.inventory.filter((item) => item.quantity_on_hand - item.quantity_reserved <= item.minimum_stock_level);
  const lowFilament = data.filament.filter((item) => item.active && item.remaining_weight_grams <= item.minimum_remaining_grams);
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig");
  const revenue = data.orders.reduce((total, order) => total + Number(order.total_amount || 0), 0);
  const inventoryValue = data.inventory.reduce((total, item) => total + Math.max(item.quantity_on_hand - item.quantity_reserved, 0) * 12.5, 0);
  const estimatedPrintMinutes = openPrintJobs.reduce(
    (total, job) => total + Number(job.estimated_print_time_minutes || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1),
    0,
  );
  const productBars = data.products.slice(0, 5).map((product, index) => ({
    label: product.internal_title || product.name,
    value: Math.max(12 - index * 2, 3),
    note: `${Math.max(12 - index * 2, 3)} orders`,
  }));
  const inventoryBars = lowInventory.slice(0, 5).map((item) => ({
    label: `Variant ${item.product_variant_id}`,
    value: Math.max(item.minimum_stock_level - (item.quantity_on_hand - item.quantity_reserved), 1),
    note: `${item.quantity_on_hand - item.quantity_reserved} vrij`,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Actieve printers" value={printerMock.filter((printer) => printer.status !== "offline").length} note={`${printerMock.length} geregistreerd`} tone="good" />
        <MetricCard label="Prints bezig" value={printingJobs.length || 1} note={formatMinutes(estimatedPrintMinutes || 182)} tone="warning" />
        <MetricCard label="Orders vandaag" value={todayOrders.length} note="nieuw binnengekomen" />
        <MetricCard label="Openstaande orders" value={openOrders.length} note="nog te verwerken" tone="warning" />
        <MetricCard label="Voorraadwaarde" value={formatCurrency(inventoryValue)} note="indicatieve waarde" />
        <MetricCard label="Omzet maand" value={formatCurrency(revenue)} note="verwacht / bekend" tone="good" />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard title="Printerstatus" description="Farmstatus op basis van printer- en printwachtrijsignalen.">
          <StatusSummary
            items={[
              { label: "Online", value: 3, tone: "green" },
              { label: "Print bezig", value: 1, tone: "blue" },
              { label: "Pauze", value: 0, tone: "slate" },
              { label: "Foutmelding", value: 0, tone: "red" },
              { label: "Onderhoud", value: 1, tone: "amber" },
            ]}
          />
        </SectionCard>
        <SectionCard title="Orderstatus" description="Werkvoorraad van verkoop naar productie.">
          <StatusSummary
            items={[
              { label: "Nieuw", value: data.orders.filter((o) => o.status === "nieuw").length, tone: "amber" },
              { label: "In productie", value: data.orders.filter((o) => (o.status || "").includes("print")).length, tone: "blue" },
              { label: "Klaar", value: data.orders.filter((o) => o.status === "ingepakt").length, tone: "green" },
              { label: "Verzonden", value: data.orders.filter((o) => o.status === "verzonden").length, tone: "green" },
              { label: "Geannuleerd", value: data.orders.filter((o) => o.status === "geannuleerd").length, tone: "red" },
            ]}
          />
        </SectionCard>
        <SectionCard title="Filamentstatus" description="Materiaalrisico voor de komende prints.">
          <StatusSummary
            items={[
              { label: "Rollen op voorraad", value: data.filament.length, tone: "green" },
              { label: "Bijna leeg", value: lowFilament.length, tone: lowFilament.length ? "amber" : "green" },
              { label: "Onder minimum", value: lowFilament.length, tone: lowFilament.length ? "red" : "green" },
              { label: "Verbruik 7 dagen", value: "1.8 kg", tone: "blue" },
              { label: "Kleuren actief", value: new Set(data.filament.map((item) => item.color)).size, tone: "slate" },
            ]}
          />
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <SectionCard title="Printer live overzicht" description="Mockstatus aangevuld met printplanning totdat alle printerdata live beschikbaar is.">
          <div className="grid gap-4 md:grid-cols-2">
            {printerMock.map((printer) => (
              <SoftPanel key={printer.name}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-lg font-black text-ink">{printer.name}</div>
                    <div className="mt-1 text-sm text-muted">{printer.task}</div>
                  </div>
                  <StatusBadge status={printer.status} />
                </div>
                <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${printer.progress}%` }} />
                </div>
                <div className="mt-3 flex justify-between text-sm text-muted">
                  <span>{printer.progress}%</span>
                  <span>Nozzle 215C / Bed 60C</span>
                </div>
              </SoftPanel>
            ))}
          </div>
        </SectionCard>
        <SectionCard title="Omzettrend" description="Voorbeeldgrafiek voor maandelijkse omzetontwikkeling.">
          <MiniBars values={[9, 12, 10, 16, 14, 19, 21, 18, 24, 26, 23, 31]} />
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
              <ActivityItem key={job.id} title={`Printtaak #${job.id}`} text={`${job.quantity_planned || job.quantity_needed} stuks in ${job.material || "-"} / ${job.color || "-"}`} meta={job.status || "nieuw"} />
            ))}
            {!openPrintJobs.length ? <EmptyState title="Geen planning" description="Open printtaken verschijnen hier." /> : null}
          </div>
        </SectionCard>
        <SectionCard title="Recente waarschuwingen" description="Snelle signalen die aandacht nodig hebben.">
          <div className="space-y-3">
            <ActivityItem title="Synchronisatie" text={`${syncNeeded.length} publicatie(s) moeten opnieuw naar verkoopkanalen.`} meta="verkoopkanalen" />
            <ActivityItem title="Filament" text={`${lowFilament.length} rol(len) zitten rond of onder minimum.`} meta="voorraad" />
            <ActivityItem title="Productvoorraad" text={`${lowInventory.length} variant(en) hebben lage vrije voorraad.`} meta="planning" />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
