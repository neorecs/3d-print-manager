import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, getOrdersData } from "@/lib/api";
import type { Order, OrderItem, OrdersData, Platform } from "@/lib/types";

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
        description="Verwerk orders vanuit verkoopplatformen en bepaal wat uit voorraad kan en wat nog geprint moet worden."
        actions={<a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/">Terug naar dashboard</a>}
      />
      {error || !data ? <OrdersError message={error || "Geen orderdata beschikbaar"} /> : <OrdersContent data={data} />}
    </AppShell>
  );
}

function OrdersError({ message }: { message: string }) {
  return (
    <SectionCard title="Orders niet bereikbaar" description="Controleer of de FastAPI backend draait.">
      <EmptyState title="Geen orderdata" description={`Orders kunnen nog niet worden geladen. Details: ${message}`} />
    </SectionCard>
  );
}

function OrdersContent({ data }: { data: OrdersData }) {
  const openOrders = data.orders.filter((order) => !["verzonden", "geannuleerd"].includes(order.status || ""));
  const fullyFromStock = data.orders.filter((order) => order.status === "volledig_uit_voorraad");
  const printNeeded = data.orders.filter((order) => ["deels_te_printen", "volledig_te_printen", "ingepland"].includes(order.status || ""));
  const unlinkedItems = data.orderItems.filter((item) => !item.product_variant_id);
  const totalRevenue = data.orders.reduce((total, order) => total + Number(order.total_amount || 0), 0);

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Orders zijn de brug tussen verkoop, voorraad en printplanning.">
        <div className="grid gap-3 md:grid-cols-3">
          <WorkflowStep title="1. Importeren" text="Orders komen binnen vanuit Etsy, Shopify of dummy-imports." />
          <WorkflowStep title="2. Voorraad controleren" text="De app reserveert vrije voorraad en berekent alleen het tekort." />
          <WorkflowStep title="3. Printtaken maken" text="Alleen wat ontbreekt gaat door naar printplanning." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Open orders" value={openOrders.length} note="nog af te handelen" />
        <MetricCard label="Uit voorraad" value={fullyFromStock.length} note="volledig leverbaar" tone="good" />
        <MetricCard label="Te printen" value={printNeeded.length} note="tekort of ingepland" tone="warning" />
        <MetricCard label="Ongekoppelde regels" value={unlinkedItems.length} note="SKU mist match" tone={unlinkedItems.length ? "danger" : "good"} />
        <MetricCard label="Omzet orders" value={formatCurrency(totalRevenue)} note="bekende orderwaarde" />
      </div>

      <SectionCard title="Orderlijst" description="Open een order om voorraadcontrole en printtaken te bekijken of acties uit te voeren.">
        {data.orders.length ? (
          <div className="space-y-3">
            {data.orders.map((order) => (
              <OrderRow
                items={data.orderItems.filter((item) => item.order_id === order.id)}
                key={order.id}
                order={order}
                platform={data.platforms.find((item) => item.id === order.platform_id)}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="Nog geen orders" description="Importeer dummydata of koppel later Etsy/Shopify om orders hier te zien." />
        )}
      </SectionCard>
    </div>
  );
}

function WorkflowStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md border-l-4 border-brand bg-slate-50 px-4 py-4">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  );
}

function OrderRow({ order, items, platform }: { order: Order; items: OrderItem[]; platform?: Platform }) {
  const ordered = items.reduce((total, item) => total + Number(item.quantity_ordered || 0), 0);
  const fromInventory = items.reduce((total, item) => total + Number(item.quantity_from_inventory || 0), 0);
  const toPrint = items.reduce((total, item) => total + Number(item.quantity_to_print || 0), 0);
  const date = order.order_date ? new Date(order.order_date).toLocaleDateString("nl-NL") : "-";

  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-card">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <a className="text-lg font-bold text-ink hover:text-brand" href={`/orders/${order.id}`}>
              {order.internal_order_number}
            </a>
            <StatusBadge status={order.status} />
          </div>
          <p className="mt-2 text-sm leading-6 text-muted">
            {platform ? `${platform.name} (${platform.type})` : `Platform ${order.platform_id}`} - {order.customer_name || "geen klantnaam"} - {date}
          </p>
          <div className="mt-3 text-sm font-semibold text-slate-700">{formatCurrency(order.total_amount)} {order.currency || "EUR"}</div>
        </div>
        <div className="grid min-w-full grid-cols-2 gap-3 sm:grid-cols-4 xl:min-w-[520px]">
          <SmallStat label="Regels" value={items.length} />
          <SmallStat label="Besteld" value={ordered} />
          <SmallStat label="Uit voorraad" value={fromInventory} />
          <SmallStat label="Te printen" value={toPrint} />
        </div>
      </div>
      <div className="mt-4 flex justify-end">
        <a className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" href={`/orders/${order.id}`}>
          Order openen
        </a>
      </div>
    </article>
  );
}

function SmallStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 px-3 py-3">
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-1 text-lg font-bold text-ink">{value}</div>
    </div>
  );
}
