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
import { ProductPrintFileManager } from "./ProductPrintFileManager";
import { TranslationManager } from "./TranslationManager";
import { VariantManager } from "./VariantManager";
import { CheckCircle2, Circle } from "lucide-react";

const tabs = [
  ["overzicht", "Overzicht"], ["informatie", "Productinformatie"], ["printbestand", "Printbestand"],
  ["varianten", "Varianten"], ["voorraad", "Voorraad"], ["fotos", "Foto's"],
  ["verkoopkanalen", "Verkoopkanalen"], ["vertalingen", "Vertalingen"], ["historie", "Historie"],
] as const;

export default async function ProductDetailPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ tab?: string }> }) {
  const { id } = await params;
  const { tab: requestedTab } = await searchParams;
  const productId = Number(id);
  const activeTab = tabs.some(([value]) => value === requestedTab) ? requestedTab! : "overzicht";
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
          <a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300" href="/catalogus">
            Terug naar catalogus
          </a>
        }
      />
      {error || !data ? <DetailError message={error || "Geen data beschikbaar"} /> : <DetailContent activeTab={activeTab} data={data} />}
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

function DetailContent({ data, activeTab }: { data: ProductDetailData; activeTab: string }) {
  const freeStock = data.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const reservedStock = data.inventory.reduce((total, item) => total + Number(item.quantity_reserved || 0), 0);
  const printMinutes = data.variants.reduce((total, variant) => total + Number(variant.estimated_print_time_minutes || 0), 0);
  const publishedCount = data.publications.filter((publication) => publication.publication_status === "gepubliceerd").length;
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig").length;
  const completeness = [
    { label: "Producttitel", complete: Boolean(data.product.internal_title || data.product.name), tab: "informatie" },
    { label: "Omschrijving", complete: Boolean(data.product.short_description || data.product.long_description), tab: "informatie" },
    { label: "Minimaal één variant", complete: data.variants.length > 0, tab: "varianten" },
    { label: "SKU en verkoopprijs", complete: data.variants.length > 0 && data.variants.every((variant) => variant.sku && Number(variant.default_sale_price || 0) > 0), tab: "varianten" },
    { label: "Printbestand", complete: Boolean(data.product.print_file_path), tab: "printbestand" },
    { label: "Hoofdfoto", complete: data.media.some((item) => item.is_primary), tab: "fotos" },
    { label: "Voorraadregel", complete: data.inventory.length > 0, tab: "voorraad" },
  ];
  const completed = completeness.filter((item) => item.complete).length;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Status" value={(data.product.status || "onbekend").replace(/_/g, " ")} />
        <MetricCard label="Varianten" value={data.variants.length} note="SKU's en printinfo" />
        <MetricCard label="Printbestand" value={data.product.print_file_path ? "Gekoppeld" : "Ontbreekt"} note="productniveau" tone={data.product.print_file_path ? "good" : "warning"} />
        <MetricCard label="Vrije voorraad" value={freeStock} note={`${reservedStock} gereserveerd`} tone="good" />
        <MetricCard label="Foto's" value={data.media.length} note={data.media.some((item) => item.is_primary) ? "hoofdfoto gekozen" : "geen hoofdfoto"} tone={data.media.length ? "good" : "warning"} />
        <MetricCard label="Publicaties" value={publishedCount} note={`${syncNeeded} sync nodig`} tone={syncNeeded ? "warning" : "neutral"} />
      </div>

      <nav aria-label="Productonderdelen" className="flex gap-2 overflow-x-auto border-b border-line pb-2">
        {tabs.map(([value, label]) => (
          <a aria-current={activeTab === value ? "page" : undefined} className={`shrink-0 rounded-md px-3 py-2 text-sm font-bold ${activeTab === value ? "bg-brand text-slate-950" : "border border-line text-slate-300 hover:border-brand"}`} href={`?tab=${value}`} key={value}>{label}</a>
        ))}
      </nav>

      {activeTab === "overzicht" ? <SectionCard title="Product gereedmaken" description={`${completed} van ${completeness.length} basiscontroles zijn afgerond.`}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {completeness.map((item) => <a className={`flex min-h-12 items-center gap-3 rounded-md border p-3 font-bold ${item.complete ? "border-emerald-400/25 bg-emerald-400/5" : "border-amber-400/30 bg-amber-400/5 hover:border-brand"}`} href={`?tab=${item.tab}`} key={item.label}>
            {item.complete ? <CheckCircle2 aria-hidden="true" className="h-5 w-5 text-emerald-300" /> : <Circle aria-hidden="true" className="h-5 w-5 text-amber-200" />}
            <span>{item.label}<span className="mt-1 block text-xs font-normal text-muted">{item.complete ? "Gereed" : "Nog invullen"}</span></span>
          </a>)}
        </div>
      </SectionCard> : null}
      {activeTab === "informatie" ? <SectionCard title="Productinformatie" description="Wijzigingen markeren gekoppelde verkoopkanalen als synchronisatie nodig."><ProductEditForm product={data.product} /></SectionCard> : null}
      {activeTab === "printbestand" ? <SectionCard title="Printbestand" description="Koppel één printklaar Bambu Studio .gcode.3mf-bestand aan het product."><ProductPrintFileManager product={data.product} variants={data.variants} printers={data.printers} /></SectionCard> : null}
      {activeTab === "varianten" ? <SectionCard title="Varianten" description="Beheer SKU's, kleur, materiaal, printtijd, filamentverbruik, afmetingen en prijzen."><VariantManager product={data.product} variants={data.variants} />{printMinutes ? <p className="mt-3 text-sm text-muted">Totale bekende printtijd: {formatMinutes(printMinutes)}.</p> : null}</SectionCard> : null}
      {activeTab === "voorraad" ? <SectionCard title="Voorraad" description="Beheer voorraad, reserveringen, minimum en opslaglocatie per variant."><InventoryManager product={data.product} variants={data.variants} inventory={data.inventory} /></SectionCard> : null}
      {activeTab === "fotos" ? <SectionCard title="Foto's" description="Upload productfoto's, kies een hoofdfoto, bepaal de volgorde en vul alt-tekst in."><MediaManager productId={data.product.id} media={data.media} /></SectionCard> : null}
      {activeTab === "verkoopkanalen" ? <SectionCard title="Verkoopkanalen" description="Beheer afwijkende titel, omschrijving, categorie, tags, prijs en publicatiestatus per kanaal."><PublicationManager product={data.product} platforms={data.platforms} publications={data.publications} /></SectionCard> : null}
      {activeTab === "vertalingen" ? <SectionCard title="Vertalingen" description="Beheer taalversies voor Duitsland, België en latere markten."><TranslationManager product={data.product} translations={data.translations} /></SectionCard> : null}
      {activeTab === "historie" ? <SectionCard title="Historie" description="Productwijzigingen en belangrijke gebeurtenissen komen hier samen."><EmptyState title="Nog geen producthistorie" description="Voorraadbewegingen zijn al traceerbaar onder Voorraad. Een gecombineerde producttijdlijn wordt opgebouwd zodra productevents beschikbaar zijn." actionHref="/voorraad" actionLabel="Voorraadbewegingen bekijken" /></SectionCard> : null}
    </div>
  );
}
