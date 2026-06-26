import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { formatMinutes, getPrintPlanningData } from "@/lib/api";
import type { PrintPlanningData } from "@/lib/types";
import { PrintPlanningManager } from "./PrintPlanningManager";

export default async function PrintPlanningPage() {
  let data: PrintPlanningData | null = null;
  let error: string | null = null;

  try {
    data = await getPrintPlanningData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Printplanning"
        description="Plan printtaken, groepeer batches en verwerk printresultaten zonder Bambu Studio te vervangen."
        actions={<a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/orders">Naar orders</a>}
      />
      {error || !data ? <PrintPlanningError message={error || "Geen printplanningdata beschikbaar"} /> : <PrintPlanningContent data={data} />}
    </AppShell>
  );
}

function PrintPlanningError({ message }: { message: string }) {
  return (
    <SectionCard title="Printplanning niet bereikbaar" description="Controleer of de FastAPI backend draait.">
      <EmptyState title="Geen printplanningdata" description={`Printplanning kan nog niet worden geladen. Details: ${message}`} />
    </SectionCard>
  );
}

function PrintPlanningContent({ data }: { data: PrintPlanningData }) {
  const openJobs = data.printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const activeJobs = data.printJobs.filter((job) => ["gepland", "bezig"].includes(job.status || ""));
  const failedJobs = data.printJobs.filter((job) => ["deels_mislukt", "mislukt"].includes(job.status || ""));
  const totalQuantity = openJobs.reduce((total, job) => total + Number(job.quantity_planned || job.quantity_needed || 0), 0);
  const totalMinutes = openJobs.reduce(
    (total, job) => total + Number(job.estimated_print_time_minutes || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1),
    0,
  );
  const totalFilament = openJobs.reduce(
    (total, job) => total + Number(job.estimated_filament_grams || 0) * Math.max(job.quantity_planned || job.quantity_needed || 1, 1),
    0,
  );

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Dit scherm organiseert printwerk. Slicing en printvoorbereiding blijven in Bambu Studio.">
        <div className="grid gap-3 md:grid-cols-3">
          <WorkflowStep title="1. Taken plannen" text="Controleer aantallen, printtijd, filament en status per printtaak." />
          <WorkflowStep title="2. Batches maken" text="Groepeer taken op materiaal en kleur zodat je efficiënter kunt printen." />
          <WorkflowStep title="3. Resultaat verwerken" text="Boek gelukte prints naar order of vrije voorraad en registreer mislukte prints." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Open printtaken" value={openJobs.length} note={`${totalQuantity} stuks`} />
        <MetricCard label="Actief gepland" value={activeJobs.length} note="gepland of bezig" tone="warning" />
        <MetricCard label="Printtijd open" value={formatMinutes(totalMinutes)} note="geschat" />
        <MetricCard label="Filament open" value={`${totalFilament}g`} note="geschat verbruik" />
        <MetricCard label="Mislukt/deels" value={failedJobs.length} note="aandacht nodig" tone={failedJobs.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Printplanning beheren" description="Maak batches, wijzig taken en verwerk printresultaten.">
        <PrintPlanningManager
          orderItems={data.orderItems}
          orders={data.orders}
          printBatches={data.printBatches}
          printJobs={data.printJobs}
          products={data.products}
          variants={data.variants}
        />
      </SectionCard>
    </div>
  );
}

function WorkflowStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md border-l-4 border-brand bg-slate-50 px-4 py-4">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  );
}
