import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getProductCatalogData } from "@/lib/api";
import type { ProductCatalogData, ProductCatalogRow } from "@/lib/types";

export default async function CatalogPage() {
  let data: ProductCatalogData | null = null;
  let error: string | null = null;

  try {
    data = await getProductCatalogData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Producten"
        description="Professionele catalogus voor verkoop, voorraad, printbestanden, kosten en platformpublicaties."
        actions={
          <div className="flex flex-wrap gap-2">
            <a className="rounded-xl border border-line px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5" href="/catalogus/ai-assistent">
              AI product assistent
            </a>
            <a className="rounded-xl bg-brand px-4 py-2 text-sm font-black text-slate-950" href="/catalogus/nieuw">
              Nieuw product
            </a>
          </div>
        }
      />
      {error || !data ? <CatalogError message={error || "Geen catalogusdata beschikbaar"} /> : <CatalogContent data={data} />}
    </AppShell>
  );
}

function CatalogError({ message }: { message: string }) {
  return (
    <SectionCard title="Catalogus niet bereikbaar" description="Controleer of de FastAPI backend draait.">
      <EmptyState title="Geen productdata" description={`Details: ${message}`} />
    </SectionCard>
  );
}

function CatalogContent({ data }: { data: ProductCatalogData }) {
  const activeProducts = data.rows.filter((row) => row.product.active !== false);
  const lowStock = data.rows.filter((row) =>
    row.inventory.some((item) => item.quantity_on_hand - item.quantity_reserved <= item.minimum_stock_level),
  );
  const published = data.rows.filter((row) => row.publications.some((publication) => publication.publication_status === "gepubliceerd"));
  const totalMargin = data.variants.reduce((total, variant) => {
    const price = Number(variant.default_sale_price || 0);
    const cost = Number(variant.cost_price || 0);
    return total + Math.max(price - cost, 0);
  }, 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Producten" value={activeProducts.length} note="actieve catalogus" />
        <MetricCard label="Varianten" value={data.variants.length} note="SKU's" />
        <MetricCard label="Lage voorraad" value={lowStock.length} note="onder minimum" tone={lowStock.length ? "warning" : "good"} />
        <MetricCard label="Gepubliceerd" value={published.length} note="op kanalen" tone="good" />
        <MetricCard label="Margepotentieel" value={formatCurrency(totalMargin)} note="op variantniveau" />
      </div>

      <SectionCard title="Productbeheer" description="Scan productfoto, SKU, voorraad, printtijd, materiaal, prijzen, marge en verkoopkanalen in een overzicht.">
        {data.rows.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {data.rows.map((row) => (
              <ProductCard key={row.product.id} row={row} />
            ))}
          </div>
        ) : (
          <EmptyState title="Nog geen producten" description="Maak je eerste product aan of gebruik de AI Product Assistent voor een concept." />
        )}
      </SectionCard>
    </div>
  );
}

function ProductCard({ row }: { row: ProductCatalogRow }) {
  const primaryVariant = row.variants[0];
  const freeStock = row.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const minimumStock = row.inventory.reduce((total, item) => total + Number(item.minimum_stock_level || 0), 0);
  const price = Number(primaryVariant?.default_sale_price || 0);
  const cost = Number(primaryVariant?.cost_price || 0);
  const margin = price ? Math.round(((price - cost) / price) * 100) : 0;
  const sku = primaryVariant?.sku || `PRD-${String(row.product.id).padStart(4, "0")}`;
  const channels = row.publications.length ? row.publications.map((publication) => `Platform ${publication.platform_id}`).join(", ") : "Nog niet gekoppeld";

  return (
    <article className="rounded-2xl border border-line bg-panelSoft p-4 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex h-32 w-full shrink-0 items-center justify-center rounded-2xl border border-line bg-gradient-to-br from-brand/25 via-sky-500/10 to-slate-900 text-3xl font-black text-brand sm:w-32">
          {(row.product.internal_title || row.product.name || "P").slice(0, 2).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <a className="text-xl font-black text-ink hover:text-brand" href={`/catalogus/${row.product.id}`}>
              {row.product.internal_title || row.product.name}
            </a>
            <StatusBadge status={row.product.status} />
          </div>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted">
            {row.product.short_description || row.product.sales_description || "Nog geen verkoopomschrijving ingevuld."}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-black text-slate-300">
            <span className="rounded-full bg-slate-800 px-2.5 py-1">{sku}</span>
            <span className="rounded-full bg-slate-800 px-2.5 py-1">{row.product.internal_category || "geen categorie"}</span>
            <span className="rounded-full bg-slate-800 px-2.5 py-1">{row.product.product_type || "3D print"}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Small label="Voorraad" value={`${freeStock} / min ${minimumStock}`} />
        <Small label="Printtijd" value={primaryVariant?.estimated_print_time_minutes ? formatMinutes(primaryVariant.estimated_print_time_minutes) : "-"} />
        <Small label="Filament" value={`${primaryVariant?.material || "-"} ${primaryVariant?.color || ""}`.trim()} />
        <Small label="Marge" value={price ? `${margin}%` : "-"} />
        <Small label="Kostprijs" value={cost ? formatCurrency(cost) : "-"} />
        <Small label="Verkoopprijs" value={price ? formatCurrency(price) : "-"} />
        <Small label="Printbestand" value={primaryVariant?.print_file_path ? "Gekoppeld" : "Ontbreekt"} />
        <Small label="Kanalen" value={channels} />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <div className="text-sm text-muted">{row.variants.length} variant(en), {row.publications.length} publicatie(s)</div>
        <a className="rounded-xl border border-line px-3 py-2 text-sm font-black text-slate-200 hover:bg-white/5" href={`/catalogus/${row.product.id}`}>
          Productdetail
        </a>
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
