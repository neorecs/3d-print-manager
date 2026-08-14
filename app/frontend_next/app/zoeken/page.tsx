import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getDashboardData } from "@/lib/api";

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const query = q.trim().toLowerCase();
  const data = await getDashboardData().catch(() => null);

  const variants = data?.variants.filter((variant) => [variant.sku, variant.variant_name, variant.color, variant.material].some((value) => value?.toLowerCase().includes(query))) || [];
  const matchingProductIds = new Set(variants.map((variant) => variant.product_id));
  const products = data?.products.filter((product) => matchingProductIds.has(product.id) || [product.name, product.internal_title, product.internal_category].some((value) => value?.toLowerCase().includes(query))) || [];
  const orders = data?.orders.filter((order) => [order.internal_order_number, order.external_order_id, order.customer_name].some((value) => value?.toLowerCase().includes(query))) || [];
  const printers = data?.printers.filter((printer) => [printer.name, printer.model, printer.host, printer.location].some((value) => value?.toLowerCase().includes(query))) || [];
  const total = products.length + orders.length + printers.length;

  return (
    <AppShell>
      <PageHeader title="Zoeken" description={query ? `${total} resultaat${total === 1 ? "" : "en"} voor “${q}”.` : "Zoek op productnaam, SKU, ordernummer, klant of printer."} />
      <form className="mb-6 flex gap-2" method="get">
        <label className="sr-only" htmlFor="page-search">Zoekterm</label>
        <input autoFocus className="min-w-0 flex-1 rounded-md border border-line bg-panel px-4 py-3 text-sm text-ink focus:border-brand" defaultValue={q} id="page-search" name="q" placeholder="Product, SKU, order, klant of printer" />
        <button className="rounded-md bg-brand px-4 py-3 text-sm font-black text-slate-950" type="submit">Zoeken</button>
      </form>
      {!query ? <EmptyState title="Vul een zoekterm in" description="Zoek bijvoorbeeld op productnaam, SKU, ordernummer of printernaam." /> : !data ? <EmptyState title="Zoeken niet beschikbaar" description="De bedrijfsgegevens konden niet worden geladen. Probeer het opnieuw." /> : (
        <div className="grid gap-5 xl:grid-cols-3">
          <SectionCard title="Producten" description={`${products.length} gevonden`}>
            {products.length ? <div className="space-y-2">{products.map((product) => <a className="block rounded-md border border-line p-3 font-bold hover:border-brand" href={`/catalogus/${product.id}`} key={product.id}>{product.internal_title || product.name}</a>)}</div> : <p className="text-sm text-muted">Geen producten gevonden.</p>}
          </SectionCard>
          <SectionCard title="Orders" description={`${orders.length} gevonden`}>
            {orders.length ? <div className="space-y-2">{orders.map((order) => <a className="block rounded-md border border-line p-3 font-bold hover:border-brand" href={`/orders/${order.id}`} key={order.id}>{order.internal_order_number}<span className="mt-1 block text-sm font-normal text-muted">{order.customer_name || "Geen klantnaam"}</span></a>)}</div> : <p className="text-sm text-muted">Geen orders gevonden.</p>}
          </SectionCard>
          <SectionCard title="Printers" description={`${printers.length} gevonden`}>
            {printers.length ? <div className="space-y-2">{printers.map((printer) => <a className="block rounded-md border border-line p-3 font-bold hover:border-brand" href="/bambu-printers" key={printer.id}>{printer.name}<span className="mt-1 block text-sm font-normal text-muted">{printer.model || printer.host}</span></a>)}</div> : <p className="text-sm text-muted">Geen printers gevonden.</p>}
          </SectionCard>
        </div>
      )}
    </AppShell>
  );
}
