import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
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
        title="Analyse en advies"
        description="Bekijk verkooptrends, marge-indicaties en uitlegbaar voorraadadvies."
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

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Verkocht 30 dagen" value={sold} note="stuks" />
        <MetricCard label="Omzet" value={formatCurrency(revenue)} note="laatste 30 dagen" />
        <MetricCard label="Geschatte winst" value={formatCurrency(profit)} note={`${margin}% marge`} tone={profit >= 0 ? "good" : "danger"} />
        <MetricCard label="Top producten" value={data.topProducts.length} note="met verkoop" />
        <MetricCard label="Open adviezen" value={openRecommendations.length} note="voorraadadvies" tone={openRecommendations.length ? "warning" : "good"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Top producten" description="Producten met de meeste verkochte aantallen in de laatste 30 dagen.">
          <AnalyticsTable rows={data.topProducts} labelKey="product" empty="Nog geen productverkoopdata." />
        </SectionCard>
        <SectionCard title="Populaire kleuren en materialen" description="Gebruik dit voor batchplanning en voorraadkeuzes.">
          <div className="grid gap-4 md:grid-cols-2">
            <AnalyticsTable rows={data.topColors} labelKey="color" empty="Geen kleurdata." compact />
            <AnalyticsTable rows={data.topMaterials} labelKey="material" empty="Geen materiaaldata." compact />
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Voorraadadvies" description="Advies is uitlegbaar: verwachte verkoop plus veiligheidsvoorraad min vrije voorraad.">
        {data.recommendations.length ? (
          <div className="space-y-3">
            {data.recommendations.map((item) => (
              <article className="rounded-lg border border-line bg-white p-4" key={item.id}>
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="font-bold text-ink">{item.product || `Product ${item.product_id}`}</div>
                      <StatusBadge status={item.status} />
                    </div>
                    <p className="mt-1 text-sm text-muted">{item.variant || item.sku || `Variant ${item.product_variant_id}`} - {item.material || "-"} / {item.color || "-"}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{item.reason || "Geen reden opgeslagen."}</p>
                  </div>
                  <div className="min-w-full xl:min-w-[420px]">
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                      <Small label="Vrij" value={item.current_free_stock} />
                      <Small label="Verwacht" value={item.expected_sales} />
                      <Small label="Veiligheid" value={item.safety_stock || 0} />
                      <Small label="Printadvies" value={item.recommended_print_quantity} />
                    </div>
                    <div className="mt-3">
                      <RecommendationActions recommendationId={item.id} />
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="Geen voorraadadvies" description="Genereer advies zodra er orderhistorie en voorraadregels zijn." />
        )}
      </SectionCard>

      <SectionCard title="Kosteninstellingen" description="Deze waarden gebruikt de backend voor winstberekeningen.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {data.costSettings.map((setting) => (
            <Small key={setting.id} label={setting.setting_name.replace(/_/g, " ")} value={setting.value} />
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function AnalyticsTable({ rows, labelKey, empty, compact = false }: { rows: AnalyticsRow[]; labelKey: keyof AnalyticsRow; empty: string; compact?: boolean }) {
  if (!rows.length) return <EmptyState title="Geen data" description={empty} />;
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr><th>{compact ? "Naam" : "Item"}</th><th className="text-right">Aantal</th><th className="text-right">Omzet</th><th className="text-right">Winst</th></tr></thead>
        <tbody>
          {rows.slice(0, compact ? 6 : 10).map((row, index) => (
            <tr key={`${String(row[labelKey])}-${index}`}>
              <td className="font-semibold">{String(row[labelKey] || "onbekend")}</td>
              <td className="text-right">{row.quantity_sold}</td>
              <td className="text-right">{formatCurrency(row.revenue)}</td>
              <td className="text-right">{formatCurrency(row.estimated_profit)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Small({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 px-3 py-3">
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="mt-1 text-lg font-bold text-ink">{value}</div>
    </div>
  );
}
