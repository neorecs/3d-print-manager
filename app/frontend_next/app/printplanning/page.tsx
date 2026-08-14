import { AppShell } from "@/components/AppShell";
import { CollapsibleHelp } from "@/components/CollapsibleHelp";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
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
        title="Productie"
        description="Plan printtaken, groepeer batches en verwerk printresultaten zonder Bambu Studio te vervangen."
        actions={<a className="rounded-xl border border-line px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5" href="/orders">Naar orders</a>}
      />
      {error || !data ? <PrintPlanningError message={error || "Geen printplanningdata beschikbaar"} /> : <PrintPlanningContent data={data} />}
    </AppShell>
  );
}

function PrintPlanningError({ message }: { message: string }) {
  return <ErrorState message={message} retryHref="/printplanning" title="Productieplanning kon niet worden geladen" />;
}

function PrintPlanningContent({ data }: { data: PrintPlanningData }) {
  const openJobs = data.printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const activeJobs = data.printJobs.filter((job) => ["gepland", "bezig"].includes(job.status || ""));
  const failedJobs = data.printJobs.filter((job) => ["deels_mislukt", "mislukt"].includes(job.status || ""));
  const totalQuantity = openJobs.reduce((total, job) => total + Number(job.quantity_planned || job.quantity_needed || 0), 0);
  const totalMinutes = openJobs.reduce(
    (total, job) => total + Number(job.estimated_print_time_minutes || 0),
    0,
  );
  const totalFilament = openJobs.reduce(
    (total, job) => total + Number(job.estimated_filament_grams || 0),
    0,
  );

  return (
    <div className="space-y-6">
      <CollapsibleHelp><p>Controleer eerst aantallen, filament en printtijd. Groepeer taken daarna per materiaal en kleur. Na het printen boek je gelukte aantallen naar de order of vrije voorraad en registreer je mislukte prints. Slicing blijft in Bambu Studio.</p></CollapsibleHelp>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Open printtaken" value={openJobs.length} note={`${totalQuantity} stuks`} />
        <MetricCard label="Actief gepland" value={activeJobs.length} note="gepland of bezig" tone="warning" />
        <MetricCard label="Printtijd open" value={formatMinutes(totalMinutes)} note="geschat" />
        <MetricCard label="Filament open" value={`${totalFilament}g`} note="geschat verbruik" />
        <MetricCard label="Mislukt/deels" value={failedJobs.length} note="aandacht nodig" tone={failedJobs.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Productie beheren" description="Maak batches, wijzig taken en verwerk printresultaten.">
        <PrintPlanningManager
          orderItems={data.orderItems}
          orders={data.orders}
          printBatches={data.printBatches}
          printJobs={data.printJobs}
          products={data.products}
          variants={data.variants}
          printers={data.printers}
        />
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
