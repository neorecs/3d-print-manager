import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getSalesChannelsData } from "@/lib/api";
import type { SalesChannelsData } from "@/lib/types";
import { SalesChannelsManager } from "./SalesChannelsManager";

export default async function SalesChannelsPage() {
  let data: SalesChannelsData | null = null;
  let error: string | null = null;
  try {
    data = await getSalesChannelsData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader title="Verkoopkanalen" description="Beheer platformen, connectorstatus en publicaties voor Etsy, Shopify en latere kanalen." />
      {error || !data ? <SectionCard title="Verkoopkanalen niet bereikbaar"><EmptyState title="Geen data" description={error || "Geen data beschikbaar"} /></SectionCard> : <SalesChannelsContent data={data} />}
    </AppShell>
  );
}

function SalesChannelsContent({ data }: { data: SalesChannelsData }) {
  const ready = data.statuses.filter((status) => status.ready_for_live);
  const syncNeeded = data.publications.filter((publication) => publication.publication_status === "synchronisatie_nodig");
  const errors = data.publications.filter((publication) => publication.publication_status === "fout" || publication.last_error);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Kanalen" value={data.platforms.length} note="geregistreerd" />
        <MetricCard label="Live klaar" value={ready.length} note="credentials compleet" tone={ready.length ? "good" : "warning"} />
        <MetricCard label="Publicaties" value={data.publications.length} note="gekoppelde producten" />
        <MetricCard label="Sync nodig" value={syncNeeded.length} note="bijwerken vereist" tone={syncNeeded.length ? "warning" : "good"} />
        <MetricCard label="Fouten" value={errors.length} note="publicatie/connectie" tone={errors.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Platformen beheren" description="Credentials zelf worden veilig in de backend opgeslagen; dit scherm toont status en basisgegevens.">
        <SalesChannelsManager platforms={data.platforms} />
      </SectionCard>

      <SectionCard title="Connectorstatus" description="Zie per kanaal welke credentials nog ontbreken voordat live import/sync veilig kan.">
        {data.statuses.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Kanaal</th><th>Type</th><th>Modus</th><th>Status</th><th>Ontbreekt</th></tr></thead>
              <tbody>
                {data.statuses.map((status) => (
                  <tr key={status.platform_id}>
                    <td className="font-semibold">{status.platform}</td>
                    <td>{status.platform_type}</td>
                    <td>{status.mode}</td>
                    <td><StatusBadge status={status.ready_for_live ? "live klaar" : "configuratie nodig"} /></td>
                    <td>{status.missing_credentials.length ? status.missing_credentials.join(", ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="Geen connectorstatus" description="Maak eerst een verkoopkanaal aan." />}
      </SectionCard>

      <SectionCard title="Publicaties met aandacht" description="Productpublicaties die synchronisatie of foutafhandeling nodig hebben.">
        {(syncNeeded.length || errors.length) ? (
          <div className="space-y-3">
            {[...syncNeeded, ...errors].slice(0, 12).map((publication) => {
              const product = data.products.find((row) => row.id === publication.product_id);
              return (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3" key={`${publication.id}-${publication.publication_status}`}>
                  <div>
                    <a className="font-bold text-ink hover:text-brand" href={`/catalogus/${publication.product_id}`}>{product?.internal_title || product?.name || `Product ${publication.product_id}`}</a>
                    <div className="mt-1 text-sm text-muted">{publication.last_error || publication.platform_title || "Geen foutmelding"}</div>
                  </div>
                  <StatusBadge status={publication.publication_status} />
                </div>
              );
            })}
          </div>
        ) : <EmptyState title="Geen publicatie-acties" description="Er zijn geen bekende publicatiefouten of sync-acties." />}
      </SectionCard>
    </div>
  );
}
