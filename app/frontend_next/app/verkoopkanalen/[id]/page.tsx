import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getSalesChannelDetailData } from "@/lib/api";
import type { SalesChannelDetailData } from "@/lib/types";
import { InventorySyncButton } from "./InventorySyncButton";
import { PlatformCredentialsManager } from "./PlatformCredentialsManager";

export default async function SalesChannelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const platformId = Number(id);
  let data: SalesChannelDetailData | null = null;
  let error: string | null = null;
  try {
    data = await getSalesChannelDetailData(platformId);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Verkoopkanaal niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title={data?.platform.name || "Verkoopkanaal"}
        description="Bekijk connectorstatus, beheer credentials en controleer gekoppelde publicaties."
        actions={<Link className="rounded-md border border-line px-3 py-2 text-sm font-bold text-ink hover:border-brand hover:text-brand" href="/verkoopkanalen">Terug naar kanalen</Link>}
      />
      {error || !data ? <SectionCard title="Kanaal niet bereikbaar"><EmptyState title="Geen data" description={error || "Geen data beschikbaar"} /></SectionCard> : <SalesChannelDetailContent data={data} />}
    </AppShell>
  );
}

function SalesChannelDetailContent({ data }: { data: SalesChannelDetailData }) {
  const missingCount = data.status?.missing_credentials.length || 0;
  const configuredCount = data.status?.configured_credentials.length || 0;
  const requiredCount = data.status?.required_credentials.length || 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Status" value={data.status?.ready_for_live ? "klaar" : "actie"} note={data.status?.ready_for_live ? "live mogelijk" : "configuratie nodig"} tone={data.status?.ready_for_live ? "good" : "warning"} />
        <MetricCard label="Vereist" value={requiredCount} note="credentials" />
        <MetricCard label="Ingevuld" value={configuredCount} note="opgeslagen" tone={configuredCount ? "good" : "warning"} />
        <MetricCard label="Ontbreekt" value={missingCount} note="nog nodig" tone={missingCount ? "warning" : "good"} />
        <MetricCard label="Publicaties" value={data.publications.length} note="op dit kanaal" />
      </div>

      <SectionCard title="Connectorstatus" description="Dit bepaalt of het kanaal klaar is voor echte import, publicatie of synchronisatie.">
        {data.status ? (
          <div className="grid gap-4 md:grid-cols-3">
            <InfoBlock title="Modus" value={data.status.mode} />
            <InfoBlock title="Status" value={data.status.ready_for_live ? "Live klaar" : "Configuratie nodig"} />
            <InfoBlock title="Type" value={data.status.platform_type} />
            <ListBlock title="Vereist" values={data.status.required_credentials} />
            <ListBlock title="Ingevuld" values={data.status.configured_credentials} />
            <ListBlock title="Ontbreekt" values={data.status.missing_credentials} warning />
          </div>
        ) : <EmptyState title="Geen connectorstatus" description="De backend gaf geen connectorstatus terug voor dit kanaal." />}
      </SectionCard>

      <SectionCard title="Credentials beheren" description="Sla tokens en sleutels op. Waarden worden na opslaan niet meer in de UI getoond.">
        <PlatformCredentialsManager platform={data.platform} status={data.status} credentials={data.credentials} />
      </SectionCard>

      <SectionCard title="Voorraad synchroniseren" description="Stuur vrije voorraad vanuit 3D Print Manager naar het verkoopkanaal.">
        <InventorySyncButton platformId={data.platform.id} platformType={data.platform.type} />
      </SectionCard>

      <SectionCard title="Publicaties op dit kanaal" description="Producten die al gekoppeld zijn aan dit verkoopkanaal.">
        {data.publications.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Product</th><th>Platformtitel</th><th>Status</th><th>Laatste sync</th><th>Fout</th></tr></thead>
              <tbody>
                {data.publications.map((publication) => {
                  const product = data.products.find((item) => item.id === publication.product_id);
                  return (
                    <tr key={publication.id}>
                      <td><Link className="font-bold text-brand hover:text-ink" href={`/catalogus/${publication.product_id}`}>{product?.internal_title || product?.name || `Product ${publication.product_id}`}</Link></td>
                      <td>{publication.platform_title || "-"}</td>
                      <td><StatusBadge status={publication.publication_status} /></td>
                      <td>{publication.last_synced_at || "-"}</td>
                      <td>{publication.last_error || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="Geen publicaties" description="Er zijn nog geen producten aan dit kanaal gekoppeld." />}
      </SectionCard>
    </div>
  );
}

function InfoBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-slate-950/25 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{title}</div>
      <div className="mt-2 font-bold text-ink">{value}</div>
    </div>
  );
}

function ListBlock({ title, values, warning }: { title: string; values: string[]; warning?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-slate-950/25 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{title}</div>
      <div className="mt-3 flex flex-wrap gap-2">
        {values.length ? values.map((value) => (
          <span className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${warning ? "bg-amber-400/10 text-amber-200 ring-amber-400/25" : "bg-slate-950/35 text-slate-300 ring-line"}`} key={value}>
            {value}
          </span>
        )) : <span className="text-sm text-muted">Geen</span>}
      </div>
    </div>
  );
}


