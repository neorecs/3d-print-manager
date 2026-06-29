import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, getOrdersData } from "@/lib/api";
import type { Order, OrderItem, OrdersData, Platform, PrintJob } from "@/lib/types";
import { ShopifyImportButton } from "./ShopifyImportButton";

export default async function OrdersPage() {
  let data: OrdersData | null = null;
  let error: string | null = null;

  try {
    data = await getOrdersData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Orders"
        description="Verkooporders vertalen naar voorraadreserveringen, printopdrachten en verzending."
        actions={<ShopifyImportButton />}
      />
      {error || !data ? <OrdersError message={error || "Geen orderdata beschikbaar"} /> : <OrdersContent data={data} />}
    </AppShell>
  );
}

function OrdersError({ message }: { message: string }) {
  return (
    <SectionCard title="Orders niet bereikbaar" description="Controleer of de FastAPI backend draait.">
      <EmptyState title="Geen orderdata" description={`Details: ${message}`} />
    </SectionCard>
  );
}

function OrdersContent({ data }: { data: OrdersData }) {
  const openOrders = data.orders.filter((order) => !["verzonden", "geannuleerd"].includes(order.status || ""));
  const paidOrders = data.orders.filter((order) => Number(order.total_amount || 0) > 0);
  const production = data.orders.filter((order) => ["deels_te_printen", "volledig_te_printen", "ingepland"].includes(order.status || ""));
  const shipped = data.orders.filter((order) => order.status === "verzonden");
  const cancelled = data.orders.filter((order) => order.status === "geannuleerd");
  const revenue = data.orders.reduce((total, order) => total + Number(order.total_amount || 0), 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Nieuw" value={data.orders.filter((order) => order.status === "nieuw").length} note="wacht op controle" tone="warning" />
        <MetricCard label="Betaald" value={paidOrders.length} note="met orderwaarde" tone="good" />
        <MetricCard label="In productie" value={production.length} note="te printen of ingepland" tone="warning" />
        <MetricCard label="Klaar" value={data.orders.filter((order) => order.status === "ingepakt").length} note="klaar voor verzending" />
        <MetricCard label="Verzonden" value={shipped.length} note="afgerond" tone="good" />
        <MetricCard label="Omzet" value={formatCurrency(revenue)} note={`${cancelled.length} geannuleerd`} />
      </div>

      <SectionCard title="Filters" description="Visuele statusfilters voor de orderflow. Klikken wordt later aangesloten op echte filtering.">
        <div className="flex flex-wrap gap-2">
          {["nieuw", "betaald", "in productie", "klaar", "verzonden", "geannuleerd"].map((filter) => (
            <span className="rounded-full border border-line bg-panelSoft px-3 py-2 text-sm font-black text-slate-200" key={filter}>
              {filter}
            </span>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Orderoverzicht" description="Elke order toont verkoopkanaal, productregels, betaling, leverdatum en gekoppelde printopdracht.">
        {data.orders.length ? (
          <div className="space-y-3">
            {data.orders.map((order) => (
              <OrderCard
                items={data.orderItems.filter((item) => item.order_id === order.id)}
                key={order.id}
                order={order}
                platform={data.platforms.find((item) => item.id === order.platform_id)}
                printJobs={data.printJobs}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="Nog geen orders" description="Importeer dummydata of Shopify/Etsy-orders om de orderflow te vullen." />
        )}
      </SectionCard>

      <SectionCard title="Importgeschiedenis" description="Laatste importresultaten per verkoopkanaal.">
        {data.importLogs.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Start</th>
                  <th>Kanaal</th>
                  <th>Status</th>
                  <th className="text-right">Nieuw</th>
                  <th className="text-right">Bijgewerkt</th>
                  <th className="text-right">Fouten</th>
                  <th>Melding</th>
                </tr>
              </thead>
              <tbody>
                {data.importLogs.slice(0, 8).map((log) => (
                  <tr key={log.id}>
                    <td>{formatDateTime(log.started_at)}</td>
                    <td>{data.platforms.find((platform) => platform.id === log.platform_id)?.name || `Platform ${log.platform_id}`}</td>
                    <td><StatusBadge status={log.status} /></td>
                    <td className="text-right">{log.created_count}</td>
                    <td className="text-right">{log.updated_count}</td>
                    <td className="text-right">{log.error_count}</td>
                    <td>{log.message || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Nog geen importgeschiedenis" description="Na de eerste import verschijnen hier aantallen en eventuele fouten." />
        )}
      </SectionCard>
    </div>
  );
}

function OrderCard({ order, items, platform, printJobs }: { order: Order; items: OrderItem[]; platform?: Platform; printJobs: PrintJob[] }) {
  const ordered = items.reduce((total, item) => total + Number(item.quantity_ordered || 0), 0);
  const toPrint = items.reduce((total, item) => total + Number(item.quantity_to_print || 0), 0);
  const linkedJob = printJobs.find((job) => items.some((item) => item.id === job.order_item_id));
  const paid = Number(order.total_amount || 0) > 0;
  const deliveryDate = order.order_date ? addDays(order.order_date, toPrint > 0 ? 5 : 2) : "-";
  const productSummary = items.map((item) => item.sku || `Regel ${item.id}`).slice(0, 2).join(", ") || "Geen regels";

  return (
    <article className="rounded-2xl border border-line bg-panelSoft p-4 shadow-card">
      <div className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <a className="text-xl font-black text-ink hover:text-brand" href={`/orders/${order.id}`}>{order.internal_order_number}</a>
            <StatusBadge status={order.status} />
          </div>
          <p className="mt-2 text-sm text-muted">{order.customer_name || "Geen klantnaam"} - {platform ? platform.name : `Platform ${order.platform_id}`}</p>
          <p className="mt-2 text-sm font-semibold text-slate-300">{productSummary}</p>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Small label="Aantal" value={ordered} />
          <Small label="Te printen" value={toPrint} />
          <Small label="Betaald" value={paid ? "Ja" : "Nee"} />
          <Small label="Leverdatum" value={deliveryDate} />
        </div>
      </div>
      <div className="mt-4 grid gap-3 border-t border-line pt-4 md:grid-cols-4">
        <Small label="Bedrag" value={formatCurrency(order.total_amount)} />
        <Small label="Kanaal" value={platform?.type || "-"} />
        <Small label="Printopdracht" value={linkedJob ? `#${linkedJob.id}` : "Niet gekoppeld"} />
        <Small label="Orderdatum" value={formatDateTime(order.order_date)} />
      </div>
    </article>
  );
}

function Small({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-slate-950/25 p-3">
      <div className="text-[11px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
      <div className="mt-1 truncate font-black text-ink" title={String(value)}>{value}</div>
    </div>
  );
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("nl-NL");
}

function addDays(value: string, days: number) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  date.setDate(date.getDate() + days);
  return date.toLocaleDateString("nl-NL");
}
