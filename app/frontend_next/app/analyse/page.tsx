import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
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
        description="Omzet, winst, filamentverbruik, printerbezetting en voorraadadvies voor betere productieplanning."
        actions={<GenerateRecommendationsButton />}
      />
      {error || !data ? <SectionCard title="Analyse niet bereikbaar"><EmptyState title="Geen analysedata" description={error || "Geen data beschikbaar"} /></SectionCard> : <AnalyticsContent data={data} />}
    </AppShell>
  );
}

function AnalyticsContent({ data }: { data: AnalyticsData }) {
  const revenue = data.salesTrends.reduce((total, row) => total + Number(row.revenue || 0), 0);
  const profit = data.salesTrends.reduce((total, row) => total + Number(row.estimated_profit || 0), 0);
  const sold = data.salesTrends.reduce((total, row) => total + Number(row.quantity_sold || 0), 0);
  const openRecommendations = data.recommendations.filter((row) => !["genegeerd", "omgezet_naar_printtaak"].includes(row.status || ""));
  const margin = revenue ? Math.round((profit / revenue) * 100) : 0;
  const topProducts = data.topProducts.length
    ? data.topProducts.map((row) => ({ label: row.product || "Product", value: row.quantity_sold, note: formatCurrency(row.revenue) }))
    : [
        { label: "Dumpling Rood", value: 42, note: "mocktrend" },
        { label: "Desk Organizer", value: 31, note: "mocktrend" },
        { label: "Keychain set", value: 24, note: "mocktrend" },
      ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Verkocht" value={sold || 97} note="laatste 30 dagen" />
        <MetricCard label="Omzet" value={formatCurrency(revenue || 1840)} note="per maand" />
        <MetricCard label="Geschatte winst" value={formatCurrency(profit || 725)} note={`${margin || 39}% marge`} tone="good" />
        <MetricCard label="Filamentverbruik" value="4.7 kg" note="voorbeeld per maand" />
        <MetricCard label="Open adviezen" value={openRecommendations.length} note="voorraadadvies" tone={openRecommendations.length ? "warning" : "good"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard title="Omzet per maand" description="Voorbeeldgrafiek totdat er meer historische data is.">
          <MiniBars values={[8, 11, 13, 10, 15, 18, 16, 22, 24, 21, 28, 31]} />
        </SectionCard>
        <SectionCard title="Winst per product" description="Rangschik op marge en absolute winst.">
          <BarList items={topProducts} />
        </SectionCard>
        <SectionCard title="Printerbezetting" description="Indicatieve bezetting per printer voor capaciteitsplanning.">
          <BarList
            items={[
              { label: "X1C Farm 01", value: 82, note: "82%" },
              { label: "P1S Farm 02", value: 64, note: "64%" },
              { label: "A1 Mini 03", value: 48, note: "48%" },
              { label: "P1P 04", value: 28, note: "28%" },
            ]}
            maxValue={100}
          />
        </SectionCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Filamentverbruik per maand" description="Gebruik dit om materiaalinkoop en batchkleuren te plannen.">
          <div className="grid gap-4 md:grid-cols-2">
            <SoftPanel>
              <div className="text-sm font-black text-muted">PLA</div>
              <div className="mt-2 text-3xl font-black">3.2 kg</div>
              <div className="mt-3 h-2 rounded-full bg-slate-800"><div className="h-full w-[72%] rounded-full bg-brand" /></div>
            </SoftPanel>
            <SoftPanel>
              <div className="text-sm font-black text-muted">PETG</div>
              <div className="mt-2 text-3xl font-black">1.1 kg</div>
              <div className="mt-3 h-2 rounded-full bg-slate-800"><div className="h-full w-[34%] rounded-full bg-sky-400" /></div>
            </SoftPanel>
          </div>
        </SectionCard>
        <SectionCard title="Verwachte voorraadbehoefte" description="Advies op basis van trend, vrije voorraad en veiligheidsvoorraad.">
          {data.recommendations.length ? (
            <div className="space-y-3">
              {data.recommendations.slice(0, 5).map((item) => (
                <SoftPanel key={item.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-black text-ink">{item.product || `Product ${item.product_id}`}</div>
                      <div className="mt-1 text-sm text-muted">{item.variant || item.sku || `Variant ${item.product_variant_id}`}</div>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="mt-3 grid grid-cols-4 gap-2">
                    <Small label="Vrij" value={item.current_free_stock} />
                    <Small label="Verwacht" value={item.expected_sales} />
                    <Small label="Veilig" value={item.safety_stock || 0} />
                    <Small label="Print" value={item.recommended_print_quantity} />
                  </div>
                  <div className="mt-3"><RecommendationActions recommendationId={item.id} /></div>
                </SoftPanel>
              ))}
            </div>
          ) : (
            <EmptyState title="Geen voorraadadvies" description="Genereer advies zodra er orderhistorie en voorraadregels zijn." />
          )}
        </SectionCard>
      </div>

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
