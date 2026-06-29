import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getFilamentData } from "@/lib/api";
import type { FilamentData } from "@/lib/types";
import { FilamentManager } from "./FilamentManager";

export default async function FilamentPage() {
  let data: FilamentData | null = null;
  let error: string | null = null;

  try {
    data = await getFilamentData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Filament"
        description="Beheer rollen, resterend gewicht, minimumvoorraad en materiaalkosten voor printplanning en marge."
        actions={<a className="rounded-xl border border-line px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5" href="/printplanning">Naar printplanning</a>}
      />
      {error || !data ? <FilamentError message={error || "Geen filamentdata beschikbaar"} /> : <FilamentContent data={data} />}
    </AppShell>
  );
}

function FilamentError({ message }: { message: string }) {
  return (
    <SectionCard title="Filament niet bereikbaar" description="Controleer of de FastAPI backend draait.">
      <EmptyState title="Geen filamentdata" description={`Filament kan nog niet worden geladen. Details: ${message}`} />
    </SectionCard>
  );
}

function FilamentContent({ data }: { data: FilamentData }) {
  const activeSpools = data.filament.filter((spool) => spool.active !== false);
  const lowSpools = activeSpools.filter((spool) => Number(spool.remaining_weight_grams || 0) <= Number(spool.minimum_remaining_grams || 0));
  const materials = new Set(activeSpools.map((spool) => spool.material).filter(Boolean));
  const totalRemaining = activeSpools.reduce((total, spool) => total + Number(spool.remaining_weight_grams || 0), 0);
  const plannedFilament = data.printJobs
    .filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""))
    .reduce((total, job) => total + Number(job.estimated_filament_grams || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1), 0);

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Filamentvoorraad is apart van productvoorraad. Dit gaat over materiaalrollen en kosten.">
        <div className="grid gap-3 md:grid-cols-3">
          <WorkflowStep title="1. Rol vastleggen" text="Registreer merk, materiaal, kleur, gewicht, prijs en locatie." />
          <WorkflowStep title="2. Gewicht bijwerken" text="Werk resterend gewicht bij na prints of bij een weegcorrectie." />
          <WorkflowStep title="3. Voorraad bewaken" text="Gebruik minimumgewicht om lage voorraad tijdig te signaleren." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Actieve rollen" value={activeSpools.length} note={`${data.filament.length} totaal`} />
        <MetricCard label="Lage voorraad" value={lowSpools.length} note="onder minimum" tone={lowSpools.length ? "danger" : "good"} />
        <MetricCard label="Materialen" value={materials.size} note="actieve types" />
        <MetricCard label="Resterend" value={`${Math.round(totalRemaining)}g`} note="actief filament" tone="good" />
        <MetricCard label="Gepland verbruik" value={`${Math.round(plannedFilament)}g`} note="open printtaken" tone="warning" />
      </div>

      <SectionCard title="Filamentrollen beheren" description="Voeg rollen toe, pas gegevens aan of werk snel het resterende gewicht bij.">
        <FilamentManager filament={data.filament} />
      </SectionCard>
    </div>
  );
}

function WorkflowStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-line border-l-4 border-l-brand bg-panelSoft px-4 py-4">
      <div className="font-black text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
    </div>
  );
}
