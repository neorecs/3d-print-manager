import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { BambuStudioOpenAction } from "@/components/BambuStudioOpenAction";
import { formatCurrency, formatMinutes, getProductCatalogData } from "@/lib/api";
import type { ProductCatalogData, ProductCatalogRow } from "@/lib/types";
import { salesBasicsMissing } from "@/lib/catalogView";

export default async function CatalogPage({ searchParams }: { searchParams: Promise<{ page?: string; view?: string }> }) {
  const query = await searchParams;
  const pageNumber = Number(query.page);
  const requestedPage = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : 1;
  const view = ["archief", "alle"].includes(query.view || "") ? query.view! : "actief";
  let data: ProductCatalogData | null = null;
  let error: string | null = null;

  try {
    data = await getProductCatalogData(requestedPage, view);
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
      {error || !data ? <CatalogError message={error || "Geen catalogusdata beschikbaar"} /> : <CatalogContent data={data} view={view} />}
    </AppShell>
  );
}

function CatalogError({ message }: { message: string }) {
  return <ErrorState message={message} retryHref="/catalogus" title="Producten konden niet worden geladen" />;
}

function CatalogContent({ data, view }: { data: ProductCatalogData; view: string }) {
  const rows = data.rows;
  const page = data.page;
  const pageCount = data.pageCount;

  return (
    <div className="space-y-6">
      <nav aria-label="Catalogusfilter" className="flex gap-2">{[["actief", "Actief"], ["archief", "Archief"], ["alle", "Alle producten"]].map(([key, label]) => <a key={key} aria-current={view === key ? "page" : undefined} className={`rounded-md px-3 py-2 text-sm font-bold ${view === key ? "bg-brand text-slate-950" : "border border-line text-muted"}`} href={`/catalogus?view=${key}`}>{label}</a>)}</nav>
      {data.printerLoadError ? <ErrorState title="Printeradvies kon niet worden geladen" message={data.printerLoadError} retryHref={`?view=${view}&page=${page}`} /> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Producten" value={data.metrics.products} note={`selectie: ${view}`} />
        <MetricCard label="Varianten" value={data.metrics.variants} note="binnen deze selectie" />
        <MetricCard label="Lage voorraad" value={data.metrics.low_stock} note="onder minimum" tone={data.metrics.low_stock ? "warning" : "good"} />
        <MetricCard label="Gepubliceerd" value={data.metrics.published} note="op kanalen" tone="good" />
        <MetricCard label="Margepotentieel" value={formatCurrency(data.metrics.margin_potential)} note="op variantniveau" />
      </div>

      <SectionCard title="Productbeheer" description="Scan productfoto, SKU, voorraad, printtijd, materiaal, prijzen, marge en verkoopkanalen in een overzicht.">
        {rows.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {rows.map((row) => (
              <ProductCard key={row.product.id} row={row} printers={data.printers} platforms={data.platforms} />
            ))}
          </div>
        ) : (
          <EmptyState title="Geen producten in deze selectie" description="Kies een andere selectie of maak een product aan." actionHref="/catalogus/nieuw" actionLabel="Product maken" />
        )}
        {pageCount > 1 ? (
          <div className="mt-5 flex items-center justify-between border-t border-line pt-4 text-sm font-bold">
            <a className={`rounded-md border border-line px-3 py-2 ${page === 1 ? "pointer-events-none opacity-40" : "hover:border-brand"}`} href={`/catalogus?view=${view}&page=${page - 1}`}>Vorige</a>
            <span className="text-muted">Pagina {page} van {pageCount}</span>
            <a className={`rounded-md border border-line px-3 py-2 ${page === pageCount ? "pointer-events-none opacity-40" : "hover:border-brand"}`} href={`/catalogus?view=${view}&page=${page + 1}`}>Volgende</a>
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

function ProductCard({ row, printers, platforms }: { row: ProductCatalogRow; printers: ProductCatalogData["printers"]; platforms: ProductCatalogData["platforms"] }) {
  const missing = salesBasicsMissing(row);
  const primaryVariant = row.variants[0];
  const freeStock = row.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const minimumStock = row.inventory.reduce((total, item) => total + Number(item.minimum_stock_level || 0), 0);
  const price = Number(primaryVariant?.default_sale_price || 0);
  const cost = Number(primaryVariant?.cost_price || 0);
  const margin = price && cost ? Math.round(((price - cost) / price) * 100) : null;
  const sku = primaryVariant?.sku || `PRD-${String(row.product.id).padStart(4, "0")}`;
  const platformNames = new Map(platforms.map((platform) => [platform.id, platform.name]));
  const channels = row.publications.length ? row.publications.map((publication) => platformNames.get(publication.platform_id) || "Onbekend kanaal").join(", ") : "Nog niet gekoppeld";

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
            <span className="text-xs text-muted">Ingestelde status: {(row.product.status || "concept").replace(/_/g, " ")}</span>
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
        <Small label="Marge" value={margin !== null ? `${margin}%` : "Nog te berekenen"} />
        <Small label="Kostprijs" value={cost ? formatCurrency(cost) : "-"} />
        <Small label="Verkoopprijs" value={price ? formatCurrency(price) : "-"} />
        <Small label="Printbestand" value={row.product.print_file_path ? "Gekoppeld" : "Ontbreekt"} />
        <Small label="Kanalen" value={channels} />
      </div>
      <a className="mt-3 block text-sm text-amber-200" href={`/catalogus/${row.product.id}?tab=verkoopkanalen`}>Publicatiecontrole: {missing.length ? `nog aanvullen: ${missing.join(", ")}` : "basis ingevuld; controleer foto's en kanaaleisen"}</a>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <div className="text-sm text-muted">{row.variants.length} variant(en), {row.publications.length} publicatie(s)</div>
        <div className="flex min-w-[15rem] flex-col gap-2 sm:flex-row">
          <BambuStudioOpenAction compact printers={printers} product={row.product} variants={row.variants} />
          <a className="rounded-md border border-line px-3 py-2 text-center text-sm font-black text-slate-200 hover:bg-white/5" href={`/catalogus/${row.product.id}`}>
            Productdetail
          </a>
        </div>
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
