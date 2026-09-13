import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { BarList, MiniBars, SoftPanel } from "@/components/ProfessionalWidgets";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, getAnalyticsData } from "@/lib/api";
import type { AnalyticsData, AnalyticsRow } from "@/lib/types";
import { GenerateRecommendationsButton, RecommendationActions } from "./RecommendationActions";

export default async function AnalyticsPage() {
  let data: AnalyticsData | null = null;
  let error: string | null = null;
  try {
    data = await getAnalyticsData(30);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Analyse"
        description="Verkooptrends en uitlegbaar voorraadadvies voor betere productieplanning."
        actions={<GenerateRecommendationsButton />}
      />
      {error || !data ? <ErrorState message={error} retryHref="/analyse" title="Analyse kon niet worden geladen" /> : <AnalyticsContent data={data} />}
    </AppShell>
  );
}

function AnalyticsContent({ data }: { data: AnalyticsData }) {
  const revenue = data.salesTrends.reduce((total, row) => total + Number(row.revenue || 0), 0);
  const profit = data.salesTrends.reduce((total, row) => total + Number(row.estimated_profit || 0), 0);
  const sold = data.salesTrends.reduce((total, row) => total + Number(row.quantity_sold || 0), 0);
  const openStatuses = new Set(["nieuw", "geaccepteerd", "aangepast"]);
  const openRecommendations = data.recommendations.filter((row) => openStatuses.has(row.status || ""));
  const recommendationHistory = data.recommendations.filter((row) => !openStatuses.has(row.status || ""));
  const margin = revenue ? Math.round((profit / revenue) * 100) : 0;
  const profitProducts = data.topProducts.map((row) => ({ label: row.product || "Product", value: Number(row.estimated_profit || 0), note: formatCurrency(row.estimated_profit || 0) }));
  const revenueBars = data.topProducts.slice(0, 12).map((row) => Number(row.revenue || 0));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Verkocht" value={sold} note="laatste 30 dagen" />
        <MetricCard label="Orderwaarde" value={formatCurrency(revenue)} note="niet-geannuleerde orders, 30 dagen" />
        <MetricCard label="Geschatte winst" value={formatCurrency(profit)} note={`${margin}% marge`} tone="good" />
        <MetricCard label="Producttrends" value={data.salesTrends.length} note="met historische data" />
        <MetricCard label="Open adviezen" value={openRecommendations.length} note="voorraadadvies" tone={openRecommendations.length ? "warning" : "good"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard title="Orderwaarde per product" description="Waarde van niet-geannuleerde orderregels in de gekozen periode.">
          {revenueBars.length ? <MiniBars values={revenueBars} /> : <EmptyState title="Nog geen omzettrend" description="De grafiek verschijnt zodra er verwerkte orderhistorie is." actionHref="/orders" actionLabel="Naar orders" />}
        </SectionCard>
        <SectionCard title="Geschatte winst per product" description="Orderwaarde min bekende variant- en geschatte filamentkosten.">
          {profitProducts.length ? <BarList items={profitProducts} /> : <EmptyState title="Nog geen winstdata" description="Verkoop- en kostengegevens zijn nodig om producten te vergelijken." actionHref="/catalogus" actionLabel="Naar producten" />}
        </SectionCard>
        <SectionCard title="Printerbezetting" description="Deze analyse is nog niet aangesloten op opgeslagen printerhistorie.">
          <EmptyState title="Bezettingsanalyse nog niet beschikbaar" description="De app slaat nog geen tijdreeks op waarmee printerbezetting betrouwbaar kan worden berekend." actionHref="/bambu-printers" actionLabel="Naar printers" />
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Filamentverbruik" description="Deze analyse is nog niet aangesloten op geboekte verbruikshistorie.">
          <EmptyState title="Verbruiksanalyse nog niet beschikbaar" description="Meer printresultaten alleen vullen dit overzicht nog niet; de meetketen moet eerst worden aangesloten." actionHref="/filament" actionLabel="Naar filament" />
        </SectionCard>
        <SectionCard title="Verwachte voorraadbehoefte" description="Advies op basis van trend, vrije voorraad en veiligheidsvoorraad.">
          {openRecommendations.length ? (
            <div className="space-y-3">
              {openRecommendations.map((item) => (
                <SoftPanel key={item.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-black text-ink">{item.product || `Product ${item.product_id}`}</div>
                      <div className="mt-1 text-sm text-muted">{item.variant || item.sku || `Variant ${item.product_variant_id}`}</div>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
                    <Small label="Vrij bij berekening" value={item.current_free_stock} />
                    <Small label="Verwacht" value={item.expected_sales} />
                    <Small label="Veilig" value={item.safety_stock || 0} />
                    <Small label="Print" value={item.recommended_print_quantity} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{item.reason || "Geen berekeningsuitleg beschikbaar."}</p>
                  <p className="mt-2 text-xs font-semibold text-muted">Berekend: {formatDateTime(item.updated_at || item.created_at)}</p>
                  <div className="mt-3"><RecommendationActions quantity={item.recommended_print_quantity} recommendationId={item.id} safetyStock={Number(item.safety_stock || 0)} status={item.status} /></div>
                </SoftPanel>
              ))}
            </div>
          ) : (
            <EmptyState title="Geen voorraadadvies" description="Genereer advies zodra er orderhistorie en voorraadregels zijn." />
          )}
        </SectionCard>
      </div>

      {recommendationHistory.length ? (
        <SectionCard title="Historie voorraadadviezen" description="Afgehandelde en vervallen adviezen blijven controleerbaar zonder actieve knoppen.">
          <details>
            <summary className="cursor-pointer font-black text-slate-200">Toon {recommendationHistory.length} afgehandelde adviezen</summary>
            <div className="mt-4 space-y-3">
              {recommendationHistory.map((item) => (
                <div className="rounded-xl border border-line bg-panelSoft p-4" key={item.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-ink">{item.product || `Product ${item.product_id}`} - {item.variant || item.sku || `Variant ${item.product_variant_id}`}</strong><StatusBadge status={item.status} /></div>
                  <p className="mt-2 text-sm text-muted">{item.reason || "Geen uitleg beschikbaar."}</p>
                  <p className="mt-2 text-xs font-semibold text-muted">Laatst berekend: {formatDateTime(item.updated_at || item.created_at)}</p>
                </div>
              ))}
            </div>
          </details>
        </SectionCard>
      ) : null}

      <SectionCard title="Trendtabellen" description="Onderliggende data blijft beschikbaar voor controle en uitleg.">
        <div className="grid gap-4 xl:grid-cols-3">
          <AnalyticsTable title="Meest verkocht" rows={data.topProducts} labelKey="product" />
          <AnalyticsTable title="Populaire kleuren" rows={data.topColors} labelKey="color" />
          <AnalyticsTable title="Populaire materialen" rows={data.topMaterials} labelKey="material" />
        </div>
      </SectionCard>
    </div>
  );
}

function formatDateTime(value?: string | null) {
  if (!value) return "onbekend";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "onbekend" : date.toLocaleString("nl-NL");
}

function AnalyticsTable({ title, rows, labelKey }: { title: string; rows: AnalyticsRow[]; labelKey: keyof AnalyticsRow }) {
  return (
    <div className="rounded-xl border border-line bg-slate-950/20 p-3">
      <div className="mb-3 font-black text-ink">{title}</div>
      {rows.length ? (
        <div className="space-y-2">
          {rows.slice(0, 6).map((row, index) => (
            <div className="flex items-center justify-between gap-3 text-sm" key={`${String(row[labelKey])}-${index}`}>
              <span className="font-bold text-slate-200">{String(row[labelKey] || "onbekend")}</span>
              <span className="text-muted">{row.quantity_sold} stuks</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">Nog geen data.</p>
      )}
    </div>
  );
}

function Small({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line bg-slate-950/30 p-2">
      <div className="text-[10px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
      <div className="mt-1 font-black text-ink">{value}</div>
    </div>
  );
}
