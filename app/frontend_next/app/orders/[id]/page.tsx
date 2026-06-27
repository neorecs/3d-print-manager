import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getOrderDetailData } from "@/lib/api";
import type { OrderDetailData, OrderItem, PrintJob, Product, ProductVariant } from "@/lib/types";
import { OrderActions } from "../OrderActions";

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const orderId = Number(id);
  let data: OrderDetailData | null = null;
  let error: string | null = null;

  try {
    data = await getOrderDetailData(orderId);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Order niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title={data?.order.internal_order_number || "Orderdetail"}
        description="Controleer orderregels, voorraadreserveringen en printtaken voor deze order."
        actions={<a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/orders">Terug naar orders</a>}
      />
      {error || !data ? <OrderError message={error || "Geen orderdata beschikbaar"} /> : <OrderContent data={data} />}
    </AppShell>
  );
}

function OrderError({ message }: { message: string }) {
  return (
    <SectionCard title="Order niet gevonden" description="Controleer of de order nog bestaat.">
      <EmptyState title="Geen orderdetail" description={message} />
    </SectionCard>
  );
}

function OrderContent({ data }: { data: OrderDetailData }) {
  const ordered = data.order.items.reduce((total, item) => total + Number(item.quantity_ordered || 0), 0);
  const fromInventory = data.order.items.reduce((total, item) => total + Number(item.quantity_from_inventory || 0), 0);
  const toPrint = data.order.items.reduce((total, item) => total + Number(item.quantity_to_print || 0), 0);
  const printMinutes = data.printJobs.reduce((total, job) => total + Number(job.estimated_print_time_minutes || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1), 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Status" value={(data.order.status || "onbekend").replace(/_/g, " ")} />
        <MetricCard label="Regels" value={data.order.items.length} note={`${ordered} stuks besteld`} />
        <MetricCard label="Uit voorraad" value={fromInventory} note="gereserveerd" tone="good" />
        <MetricCard label="Te printen" value={toPrint} note={data.printJobs.length ? `${data.printJobs.length} printtaken` : "nog geen printtaken"} tone={toPrint ? "warning" : "neutral"} />
        <MetricCard label="Orderwaarde" value={formatCurrency(data.order.total_amount)} note={data.order.currency || "EUR"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
        <SectionCard title="Orderinformatie" description="Brongegevens vanuit het verkoopplatform.">
          <div className="grid gap-3 md:grid-cols-2">
            <InfoRow label="Platform" value={data.platform ? `${data.platform.name} (${data.platform.type})` : `Platform ${data.order.platform_id}`} />
            <InfoRow label="Extern ordernummer" value={data.order.external_order_id || "-"} />
            <InfoRow label="Klant" value={data.order.customer_name || "-"} />
            <InfoRow label="E-mail" value={data.order.customer_email || "-"} />
            <InfoRow label="Orderdatum" value={data.order.order_date ? new Date(data.order.order_date).toLocaleString("nl-NL") : "-"} />
            <InfoRow label="Status" value={<StatusBadge status={data.order.status} />} />
          </div>
        </SectionCard>

        <SectionCard title="Orderacties" description="Voer acties bewust in deze volgorde uit.">
          <OrderActions accountingSale={data.accountingSale} orderId={data.order.id} />
        </SectionCard>
      </div>

      <SectionCard title="Orderregels" description="Per regel zie je of de voorraad is gebruikt of dat er nog printwerk nodig is.">
        {data.order.items.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Product</th>
                  <th>Variant</th>
                  <th>Status voorraad</th>
                  <th className="text-right">Besteld</th>
                  <th className="text-right">Voorraad</th>
                  <th className="text-right">Printen</th>
                  <th className="text-right">Prijs</th>
                </tr>
              </thead>
              <tbody>
                {data.order.items.map((item) => (
                  <OrderItemRow
                    item={item}
                    key={item.id}
                    product={data.products.find((product) => product.id === item.product_id)}
                    variant={data.variants.find((variant) => variant.id === item.product_variant_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Geen orderregels" description="Deze order heeft nog geen regels. Importeer of voeg regels toe via de backend." />
        )}
      </SectionCard>

      <SectionCard title="Gekoppelde printtaken" description={printMinutes ? `Geschatte printtijd: ${formatMinutes(printMinutes)}.` : "Printtaken verschijnen hier na voorraadcontrole en aanmaken van printtaken."}>
        {data.printJobs.length ? (
          <div className="space-y-3">
            {data.printJobs.map((job) => (
              <PrintJobRow key={job.id} job={job} variant={data.variants.find((variant) => variant.id === job.product_variant_id)} />
            ))}
          </div>
        ) : (
          <EmptyState title="Geen printtaken" description="Als er na voorraadcontrole tekort is, kun je met de knop hierboven printtaken aanmaken." />
        )}
      </SectionCard>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 px-3 py-3">
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function OrderItemRow({ item, product, variant }: { item: OrderItem; product?: Product; variant?: ProductVariant }) {
  return (
    <tr>
      <td className="font-semibold">{item.sku || "-"}</td>
      <td>{product?.internal_title || product?.name || (item.product_id ? `Product ${item.product_id}` : "Niet gekoppeld")}</td>
      <td>{variant?.variant_name || variant?.sku || (item.product_variant_id ? `Variant ${item.product_variant_id}` : "Niet gekoppeld")}</td>
      <td><StatusBadge status={item.inventory_status} /></td>
      <td className="text-right font-semibold">{item.quantity_ordered}</td>
      <td className="text-right">{item.quantity_from_inventory}</td>
      <td className="text-right">{item.quantity_to_print}</td>
      <td className="text-right font-semibold">{formatCurrency(item.unit_sale_price)}</td>
    </tr>
  );
}

function PrintJobRow({ job, variant }: { job: PrintJob; variant?: ProductVariant }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="font-bold text-ink">Printtaak #{job.id}</div>
          <p className="mt-1 text-sm text-muted">
            {variant?.variant_name || variant?.sku || `Variant ${job.product_variant_id}`} - {job.material || variant?.material || "-"} / {job.color || variant?.color || "-"}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <SmallStat label="Nodig" value={job.quantity_needed} />
        <SmallStat label="Gepland" value={job.quantity_planned} />
        <SmallStat label="Gelukt" value={job.quantity_succeeded || 0} />
        <SmallStat label="Mislukt" value={job.quantity_failed || 0} />
      </div>
    </div>
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
