import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getProductCatalogData } from "@/lib/api";
import type { ProductCatalogData, ProductCatalogRow, ProductPublication } from "@/lib/types";

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
        title="Productcatalogus"
        description="Beheer interne producten als hoofdbron voor voorraad, publicaties, orderverwerking en printplanning."
        actions={
          <div className="flex flex-wrap gap-2">
            <a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/">
              Terug naar dashboard
            </a>
            <a className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white" href="/catalogus/nieuw">
              Nieuw product maken
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
      <EmptyState
        title="Geen productdata"
        description={`De catalogus kan nog niet worden geladen. Details: ${message}`}
      />
    </SectionCard>
  );
}

function CatalogContent({ data }: { data: ProductCatalogData }) {
  const activeProducts = data.rows.filter((row) => row.product.active !== false);
  const publishReady = data.rows.filter((row) => row.product.status === "klaar_voor_publicatie");
  const published = data.rows.filter((row) => row.publications.some((publication) => publication.publication_status === "gepubliceerd"));
  const syncNeeded = data.rows.filter((row) =>
    row.publications.some((publication) => publication.publication_status === "synchronisatie_nodig"),
  );
  const totalFreeStock = data.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Begin altijd met de interne productbasis. Platformen zoals Etsy en Shopify volgen daarna.">
        <div className="grid gap-3 md:grid-cols-3">
          <WorkflowStep
            title="1. Productbasis"
            text="Leg naam, verkooptekst, categorie, producttype, SEO en status vast."
          />
          <WorkflowStep
            title="2. Varianten"
            text="Maak uitvoeringen met SKU, kleur, materiaal, printtijd, filamentverbruik en prijs."
          />
          <WorkflowStep
            title="3. Publiceren"
            text="Controleer foto’s, voorraad en platformvelden voordat je naar verkoopkanalen synchroniseert."
          />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Producten" value={activeProducts.length} note="actieve interne basis" />
        <MetricCard label="Varianten" value={data.variants.length} note="SKU's en printinfo" />
        <MetricCard label="Vrije voorraad" value={totalFreeStock} note="klaar voor verkoop" tone="good" />
        <MetricCard label="Publiceerbaar" value={publishReady.length} note="klaar voor controle" tone="warning" />
        <MetricCard label="Sync nodig" value={syncNeeded.length} note={`${published.length} gepubliceerd`} tone="warning" />
      </div>

      <SectionCard
        title="Producten"
        description="Scan hier snel of een product compleet genoeg is voor voorraad, printplanning en publicatie."
      >
        {data.rows.length ? (
          <div className="space-y-3">
            {data.rows.map((row) => (
              <ProductRow key={row.product.id} row={row} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Nog geen producten"
            description="Maak je eerste interne product aan voordat je varianten, foto's of platformpublicaties toevoegt."
          />
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

function ProductRow({ row }: { row: ProductCatalogRow }) {
  const variantCount = row.variants.length;
  const freeStock = row.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const printMinutes = row.variants.reduce((total, variant) => total + Number(variant.estimated_print_time_minutes || 0), 0);
  const salePrices = row.variants.map((variant) => Number(variant.default_sale_price || 0)).filter(Boolean);
  const lowestPrice = salePrices.length ? Math.min(...salePrices) : null;

  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-card">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <a className="text-lg font-bold text-ink hover:text-brand" href={`/catalogus/${row.product.id}`}>
              {row.product.internal_title || row.product.name}
            </a>
            <StatusBadge status={row.product.status} />
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            {row.product.short_description || row.product.sales_description || row.product.long_description || "Nog geen korte omschrijving ingevuld."}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-slate-600">
            <span className="rounded-full bg-slate-100 px-2.5 py-1">Product-ID #{row.product.id}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">{row.product.internal_category || "geen categorie"}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">{row.product.product_type || "geen producttype"}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">{row.product.active === false ? "inactief" : "actief"}</span>
          </div>
        </div>

        <div className="grid min-w-full grid-cols-2 gap-3 sm:grid-cols-4 xl:min-w-[520px]">
          <SmallStat label="Varianten" value={variantCount} />
          <SmallStat label="Vrije voorraad" value={freeStock} />
          <SmallStat label="Printtijd" value={printMinutes ? formatMinutes(printMinutes) : "-"} />
          <SmallStat label="Vanaf prijs" value={lowestPrice ? formatCurrency(lowestPrice) : "-"} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 border-t border-line pt-4 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="text-xs font-bold uppercase text-muted">Varianten</div>
          {row.variants.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {row.variants.slice(0, 6).map((variant) => (
                <span className="rounded-md border border-line bg-slate-50 px-3 py-2 text-sm" key={variant.id}>
                  <strong>{variant.variant_name || variant.sku || `Variant ${variant.id}`}</strong>
                  <span className="ml-2 text-muted">{variant.material || "-"} / {variant.color || "-"}</span>
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-amber-700">Voeg minimaal een variant toe voordat dit product verkoopklaar is.</p>
          )}
        </div>

        <PublicationSummary publications={row.publications} />
      </div>
      <div className="mt-4 flex justify-end">
        <a className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" href={`/catalogus/${row.product.id}`}>
          Product openen
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

function PublicationSummary({ publications }: { publications: ProductPublication[] }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase text-muted">Platformpublicatie</div>
      {publications.length ? (
        <div className="mt-2 space-y-2">
          {publications.map((publication) => (
            <div className="flex items-center justify-between gap-3 rounded-md border border-line px-3 py-2" key={publication.id}>
              <span className="text-sm font-semibold">Platform {publication.platform_id}</span>
              <StatusBadge status={publication.publication_status} />
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted">Nog niet gekoppeld aan Etsy, Shopify of een ander verkoopkanaal.</p>
      )}
    </div>
  );
}
