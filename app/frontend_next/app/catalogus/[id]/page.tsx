import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { formatMinutes, getProductDetailData } from "@/lib/api";
import type { ProductDetailData } from "@/lib/types";
import { InventoryManager } from "./InventoryManager";
import { MediaManager } from "./MediaManager";
import { PublicationManager } from "./PublicationManager";
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

        <SectionCard title="Productvoorraad beheren" description="Leg voorraad, reserveringen, minimumvoorraad en opslaglocatie per variant vast.">
          <InventoryManager product={data.product} variants={data.variants} inventory={data.inventory} />
        </SectionCard>

        <SectionCard title="Foto's beheren" description="Upload productfoto's, kies een hoofdfoto, bepaal volgorde en vul alt-tekst in.">
          <MediaManager productId={data.product.id} media={data.media} />
        </SectionCard>

        <SectionCard title="Platformpublicaties beheren" description="Leg per platform afwijkende titel, omschrijving, categorie, tags, prijs en status vast.">
          <PublicationManager product={data.product} platforms={data.platforms} publications={data.publications} />
        </SectionCard>
      </div>
    </div>
  );
}
