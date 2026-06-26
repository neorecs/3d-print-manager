import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, formatMinutes, getProductDetailData } from "@/lib/api";
import type { ProductDetailData, ProductPublication } from "@/lib/types";
import { MediaManager } from "./MediaManager";
import { ProductEditForm } from "./ProductEditForm";
import { VariantManager } from "./VariantManager";

export default async function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const productId = Number(id);
  let data: ProductDetailData | null = null;
  let error: string | null = null;

  try {
    data = await getProductDetailData(productId);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Product niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title={data?.product.internal_title || data?.product.name || "Productdetail"}
        description="Beheer de interne productbasis en controleer varianten, foto's, voorraad en platformpublicaties."
        actions={
          <a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/catalogus">
            Terug naar catalogus
          </a>
        }
      />
      {error || !data ? <DetailError message={error || "Geen data beschikbaar"} /> : <DetailContent data={data} />}
    </AppShell>
  );
}

function DetailError({ message }: { message: string }) {
  return (
    <SectionCard title="Product niet gevonden" description="Controleer of het product nog bestaat.">
      <EmptyState title="Geen productdetail" description={message} />
    </SectionCard>
  );
}

function DetailContent({ data }: { data: ProductDetailData }) {
  const freeStock = data.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const reservedStock = data.inventory.reduce((total, item) => total + Number(item.quantity_reserved || 0), 0);
  const printMinutes = data.variants.reduce((total, variant) => total + Number(variant.estimated_print_time_minutes || 0), 0);
  const publishedCount = data.publications.filter((publication) => publication.publication_status === "gepubliceerd").length;
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig").length;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Status" value={(data.product.status || "onbekend").replace(/_/g, " ")} />
        <MetricCard label="Varianten" value={data.variants.length} note="SKU's en printinfo" />
        <MetricCard label="Vrije voorraad" value={freeStock} note={`${reservedStock} gereserveerd`} tone="good" />
        <MetricCard label="Foto's" value={data.media.length} note={data.media.some((item) => item.is_primary) ? "hoofdfoto gekozen" : "geen hoofdfoto"} tone={data.media.length ? "good" : "warning"} />
        <MetricCard label="Publicaties" value={publishedCount} note={`${syncNeeded} sync nodig`} tone={syncNeeded ? "warning" : "neutral"} />
      </div>

      <SectionCard title="Productbasis bewerken" description="Wijzigingen hier markeren gekoppelde platformpublicaties als synchronisatie nodig.">
        <ProductEditForm product={data.product} />
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Varianten beheren" description="Maak en wijzig SKU's, kleur, materiaal, printtijd, filamentverbruik, afmetingen en prijzen.">
          <VariantManager product={data.product} variants={data.variants} />
          {printMinutes ? <p className="mt-3 text-sm text-muted">Totale bekende printtijd: {formatMinutes(printMinutes)}.</p> : null}
        </SectionCard>

        <SectionCard title="Productvoorraad" description="Vrije voorraad is op voorraad min gereserveerd.">
          {data.inventory.length ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Materiaal</th>
                    <th>Kleur</th>
                    <th className="text-right">Vrij</th>
                    <th>Locatie</th>
                  </tr>
                </thead>
                <tbody>
                  {data.inventory.map((item) => (
                    <tr key={item.id}>
                      <td>{item.product_variant_id}</td>
                      <td>{item.material || "-"}</td>
                      <td>{item.color || "-"}</td>
                      <td className="text-right font-semibold">{Math.max(item.quantity_on_hand - item.quantity_reserved, 0)}</td>
                      <td>{item.location || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="Geen productvoorraad" description="Voorraadregels verschijnen hier zodra voorraad voor varianten wordt aangemaakt." />
          )}
        </SectionCard>

        <SectionCard title="Foto's beheren" description="Upload productfoto's, kies een hoofdfoto, bepaal volgorde en vul alt-tekst in.">
          <MediaManager productId={data.product.id} media={data.media} />
        </SectionCard>

        <SectionCard title="Platformpublicaties" description="Per platform zie je publicatiestatus, sync-status en eventuele foutmelding.">
          {data.publications.length ? (
            <div className="space-y-3">
              {data.publications.map((publication) => (
                <PublicationCard publication={publication} key={publication.id} />
              ))}
            </div>
          ) : (
            <EmptyState title="Nog geen platformpublicaties" description="Koppel dit product later aan Etsy, Shopify of andere verkoopkanalen." />
          )}
        </SectionCard>
      </div>
    </div>
  );
}

function PublicationCard({ publication }: { publication: ProductPublication }) {
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">Platform {publication.platform_id}</div>
          <div className="mt-1 text-sm text-muted">{publication.platform_title || "Geen afwijkende titel"}</div>
        </div>
        <StatusBadge status={publication.publication_status} />
      </div>
      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div><span className="font-semibold">Categorie:</span> {publication.platform_category || "-"}</div>
        <div><span className="font-semibold">Prijs:</span> {publication.platform_price_override ? formatCurrency(publication.platform_price_override) : "-"}</div>
        <div><span className="font-semibold">Laatste sync:</span> {publication.last_synced_at || "-"}</div>
        <div><span className="font-semibold">Tags:</span> {publication.platform_tags || "-"}</div>
      </div>
      {publication.last_error ? <p className="mt-3 text-sm font-semibold text-red-700">{publication.last_error}</p> : null}
    </div>
  );
}
