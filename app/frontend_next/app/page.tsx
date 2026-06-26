import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
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
        title="Dashboard"
        description="Centrale startpagina voor orders, voorraad, printplanning en publicaties die aandacht nodig hebben."
        actions={<a className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white" href="/">Ververs overzicht</a>}
      />
      {error || !data ? <DashboardError message={error || "Geen data beschikbaar"} /> : <DashboardContent data={data} />}
    </AppShell>
  );
}

function DashboardError({ message }: { message: string }) {
  return (
    <SectionCard title="Backend niet bereikbaar" description="Start Docker Compose of controleer de API-url.">
      <EmptyState
        title="Nog geen dashboarddata"
        description={`De Next.js frontend kan de FastAPI backend nog niet lezen. Details: ${message}`}
      />
    </SectionCard>
  );
}

function DashboardContent({ data }: { data: DashboardData }) {
  const openOrders = data.orders.filter((order) => !["verzonden", "geannuleerd", "afgerond"].includes(order.status || ""));
  const printNeededOrders = data.orders.filter((order) => (order.status || "").includes("print"));
  const openPrintJobs = data.printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const lowInventory = data.inventory.filter(
    (item) => item.quantity_on_hand - item.quantity_reserved <= item.minimum_stock_level,
  );
  const lowFilament = data.filament.filter(
    (item) => item.active && item.remaining_weight_grams <= item.minimum_remaining_grams,
  );
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig");
  const revenue = data.orders.reduce((total, order) => total + Number(order.total_amount || 0), 0);
  const estimatedPrintMinutes = openPrintJobs.reduce(
    (total, job) => total + Number(job.estimated_print_time_minutes || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1),
    0,
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Open orders" value={openOrders.length} note="nog te verwerken" />
        <MetricCard label="Te printen orders" value={printNeededOrders.length} note="met printactie" tone="warning" />
        <MetricCard label="Open printtaken" value={openPrintJobs.length} note={formatMinutes(estimatedPrintMinutes)} />
        <MetricCard label="Lage voorraad" value={lowInventory.length + lowFilament.length} note="product + filament" tone="danger" />
        <MetricCard label="Sync nodig" value={syncNeeded.length} note={formatCurrency(revenue)} tone="warning" />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Vandaag afhandelen" description="Orders die nog aandacht nodig hebben.">
          {openOrders.length ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Klant</th>
                    <th>Status</th>
                    <th className="text-right">Bedrag</th>
                  </tr>
                </thead>
                <tbody>
                  {openOrders.slice(0, 8).map((order) => (
                    <tr key={order.id}>
                      <td className="font-semibold">{order.internal_order_number}</td>
                      <td>{order.customer_name || "-"}</td>
                      <td><StatusBadge status={order.status} /></td>
                      <td className="text-right font-semibold">{formatCurrency(order.total_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="Geen open orders" description="Er staan geen orders klaar voor verwerking." />
          )}
        </SectionCard>

        <SectionCard title="Printplanning" description="Open printtaken gegroepeerd voor productieplanning.">
          {openPrintJobs.length ? (
            <div className="space-y-3">
              {openPrintJobs.slice(0, 6).map((job) => (
                <div className="flex items-center justify-between rounded-md border border-line bg-slate-50 px-3 py-3" key={job.id}>
                  <div>
                    <div className="font-semibold">Printtaak #{job.id}</div>
                    <div className="mt-1 text-sm text-muted">{job.material || "-"} / {job.color || "-"}</div>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={job.status} />
                    <div className="mt-1 text-sm font-semibold">{job.quantity_planned || job.quantity_needed} stuks</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Geen open printtaken" description="Nieuwe printtaken verschijnen hier zodra orders of voorraadadvies daarom vragen." />
          )}
        </SectionCard>

        <SectionCard title="Voorraadadvies" description="Adviezen die nog geaccepteerd, aangepast of genegeerd moeten worden.">
          {data.recommendations.length ? (
            <div className="space-y-3">
              {data.recommendations.slice(0, 6).map((recommendation) => (
                <div className="rounded-md border border-line px-3 py-3" key={recommendation.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold">Variant #{recommendation.product_variant_id}</div>
                      <p className="mt-1 text-sm text-muted">
                        Advies: print {recommendation.recommended_print_quantity} extra. Vrije voorraad: {recommendation.current_free_stock}.
                      </p>
                    </div>
                    <StatusBadge status={recommendation.status} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Geen voorraadadvies" description="Genereer adviezen zodra er voldoende orderhistorie is." />
          )}
        </SectionCard>

        <SectionCard title="Publicaties met aandacht nodig" description="Productpublicaties die opnieuw gesynchroniseerd of gecontroleerd moeten worden.">
          {syncNeeded.length ? (
            <div className="space-y-3">
              {syncNeeded.slice(0, 6).map((publication) => (
                <div className="flex items-center justify-between rounded-md border border-line px-3 py-3" key={publication.id}>
                  <div>
                    <div className="font-semibold">Product #{publication.product_id}</div>
                    <div className="mt-1 text-sm text-muted">Platform #{publication.platform_id}</div>
                  </div>
                  <StatusBadge status={publication.publication_status} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Geen sync-acties" description="Alle bekende publicaties zijn op dit moment rustig." />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
