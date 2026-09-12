import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { formatMinutes, getProductDetailData } from "@/lib/api";
import type { ProductDetailData } from "@/lib/types";
import { salesBasicsMissing } from "@/lib/catalogView";
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
  ["verkoopkanalen", "Verkoopkanalen"], ["vertalingen", "Vertalingen"],
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
  return <ErrorState title="Product kon niet worden geladen" message={message} retryHref="?" />;
}

function DetailContent({ data, activeTab }: { data: ProductDetailData; activeTab: string }) {
  const missing = salesBasicsMissing(data);
  const freeStock = data.inventory.reduce(
    (total, item) => total + Math.max(Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0), 0),
    0,
  );
  const reservedStock = data.inventory.reduce((total, item) => total + Number(item.quantity_reserved || 0), 0);
  const printMinutes = data.variants.reduce((total, variant) => total + Number(variant.estimated_print_time_minutes || 0), 0);
  const publishedCount = data.publications.filter((publication) => publication.publication_status === "gepubliceerd").length;
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig").length;
  const completeness = [
    { label: "Producttitel", complete: !missing.includes("titel"), tab: "informatie" },
    { label: "Omschrijving", complete: !missing.includes("omschrijving"), tab: "informatie" },
    { label: "Minimaal één actieve variant", complete: !missing.includes("variant"), tab: "varianten" },
    { label: "SKU en verkoopprijs", complete: !missing.includes("variant") && !missing.includes("SKU of prijs"), tab: "varianten" },
    { label: "Materiaal en kleur", complete: !missing.includes("variant") && !missing.includes("materiaal of kleur"), tab: "varianten" },
    { label: "Hoofdfoto", complete: data.loadErrors.media ? null : data.media.some((item) => item.is_primary), tab: "fotos" },
  ];
  const completed = completeness.filter((item) => item.complete).length;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Ingestelde status" value={(data.product.status || "onbekend").replace(/_/g, " ")} note="geen publicatiecontrole" />
        <MetricCard label="Varianten" value={data.variants.length} note="SKU's en printinfo" />
        <MetricCard label="Printbestand" value={data.product.print_file_path ? "Gekoppeld" : "Ontbreekt"} note="productniveau" tone={data.product.print_file_path ? "good" : "warning"} />
        <MetricCard label="Vrije voorraad" value={freeStock} note={`${reservedStock} gereserveerd`} tone="good" />
        <MetricCard label="Foto's" value={data.loadErrors.media ? "Onbekend" : data.media.length} note={data.loadErrors.media ? "laden mislukt" : data.media.some((item) => item.is_primary) ? "hoofdfoto gekozen" : "geen hoofdfoto"} tone="neutral" />
        <MetricCard label="Publicaties" value={data.loadErrors.publications ? "Onbekend" : publishedCount} note={data.loadErrors.publications ? "laden mislukt" : `${syncNeeded} sync nodig`} tone="neutral" />
      </div>

      <nav aria-label="Productonderdelen" className="flex gap-2 overflow-x-auto border-b border-line pb-2">
        {tabs.map(([value, label]) => (
          <a aria-current={activeTab === value ? "page" : undefined} className={`shrink-0 rounded-md px-3 py-2 text-sm font-bold ${activeTab === value ? "bg-brand text-slate-950" : "border border-line text-slate-300 hover:border-brand"}`} href={`?tab=${value}`} key={value}>{label}</a>
        ))}
      </nav>

      {activeTab === "overzicht" ? <SectionCard title="Verkoop voorbereiden" description={`${completed} van ${completeness.length} basisgegevens ingevuld. De definitieve publicatiecontrole gebeurt per verkoopkanaal.`}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {completeness.map((item) => <a className={`flex min-h-12 items-center gap-3 rounded-md border p-3 font-bold ${item.complete ? "border-emerald-400/25 bg-emerald-400/5" : "border-amber-400/30 bg-amber-400/5 hover:border-brand"}`} href={`?tab=${item.tab}`} key={item.label}>
            {item.complete ? <CheckCircle2 aria-hidden="true" className="h-5 w-5 text-emerald-300" /> : <Circle aria-hidden="true" className="h-5 w-5 text-amber-200" />}
            <span>{item.label}<span className="mt-1 block text-xs font-normal text-muted">{item.complete === null ? "Onbekend: laden mislukt" : item.complete ? "Ingevuld" : "Nog invullen"}</span></span>
          </a>)}
        </div>
      </SectionCard> : null}
      {activeTab === "overzicht" ? <SectionCard title="Printen voorbereiden" description="Los van verkoopprijs, foto's en publicatie."><a className="font-bold text-brand" href="?tab=printbestand">{data.product.print_file_path ? "Bestand gekoppeld: openen in Bambu Studio" : "Printbestand toevoegen"}</a></SectionCard> : null}
      {Object.entries(data.loadErrors).map(([section, message]) => <ErrorState key={section} title={`${({ media: "Foto's", tags: "Tags", translations: "Vertalingen", publications: "Publicaties", printers: "Printeradvies" } as Record<string, string>)[section]} konden niet worden geladen`} message={message} retryHref={`?tab=${activeTab}`} />)}
      {activeTab === "informatie" ? <SectionCard title="Productinformatie" description="Wijzigingen markeren gekoppelde verkoopkanalen als synchronisatie nodig."><ProductEditForm product={data.product} /></SectionCard> : null}
      {activeTab === "printbestand" ? <SectionCard title="Productbestand" description="Koppel één bronmodel, Bambu Studio-project of geslicet bestand aan het product."><ProductPrintFileManager product={data.product} variants={data.variants} printers={data.printers} /></SectionCard> : null}
      {activeTab === "varianten" ? <SectionCard title="Varianten" description="Beheer SKU's, kleur, materiaal, printtijd, filamentverbruik, afmetingen en prijzen."><VariantManager product={data.product} variants={data.variants} />{printMinutes ? <p className="mt-3 text-sm text-muted">Totale bekende printtijd: {formatMinutes(printMinutes)}.</p> : null}</SectionCard> : null}
      {activeTab === "voorraad" ? <SectionCard title="Voorraad" description="Beheer voorraad, reserveringen, minimum en opslaglocatie per variant."><InventoryManager product={data.product} variants={data.variants} inventory={data.inventory} /></SectionCard> : null}
      {activeTab === "fotos" && !data.loadErrors.media ? <SectionCard title="Foto's" description="Upload productfoto's, kies een hoofdfoto, bepaal de volgorde en vul alt-tekst in."><MediaManager productId={data.product.id} media={data.media} /></SectionCard> : null}
      {activeTab === "verkoopkanalen" && !data.loadErrors.publications ? <SectionCard title="Verkoopkanalen" description="Beheer afwijkende titel, omschrijving, categorie, tags, prijs en publicatiestatus per kanaal."><PublicationManager product={data.product} platforms={data.platforms} publications={data.publications} /></SectionCard> : null}
      {activeTab === "vertalingen" && !data.loadErrors.translations ? <SectionCard title="Vertalingen" description="Beheer taalversies voor Duitsland, België en latere markten."><TranslationManager product={data.product} translations={data.translations} /></SectionCard> : null}
    </div>
  );
}
