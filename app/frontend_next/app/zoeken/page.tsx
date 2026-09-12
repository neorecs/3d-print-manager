import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getSearchData } from "@/lib/api";

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const query = q.trim().toLowerCase();
  const data = query.length >= 2 ? await getSearchData(query).catch(() => null) : null;
  const products = data?.products || [];
  const orders = data?.orders || [];
  const printers = data?.printers || [];
  const total = products.length + orders.length + printers.length;

  return (
    <AppShell>
      <PageHeader title="Zoeken" description={query ? `${total} resultaat${total === 1 ? "" : "en"} voor “${q}”.` : "Zoek op productnaam, SKU, ordernummer, klant of printer."} />
      <form className="mb-6 flex gap-2" method="get">
        <label className="sr-only" htmlFor="page-search">Zoekterm</label>
        <input autoFocus className="min-w-0 flex-1 rounded-md border border-line bg-panel px-4 py-3 text-sm text-ink focus:border-brand" defaultValue={q} id="page-search" name="q" placeholder="Product, SKU, order, klant of printer" />
        <button className="rounded-md bg-brand px-4 py-3 text-sm font-black text-slate-950" type="submit">Zoeken</button>
      </form>
      {query.length < 2 ? <EmptyState title="Vul minimaal twee tekens in" description="Zoek bijvoorbeeld op productnaam, SKU, ordernummer of printernaam." /> : !data ? <EmptyState title="Zoeken niet beschikbaar" description="De bedrijfsgegevens konden niet worden geladen. Probeer het opnieuw." /> : (
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
