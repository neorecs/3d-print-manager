import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getBambuPrintersData } from "@/lib/api";
import type { BambuPrintersData } from "@/lib/types";
import { BambuPrinterManager } from "./BambuPrinterManager";

export const dynamic = "force-dynamic";

export default async function BambuPrintersPage() {
  const data = await getBambuPrintersData().catch(() => ({ printers: [] }));

  return (
    <AppShell>
      <PageHeader
        title="Bambu printers"
        description="Registreer je Bambu-printers voor read-only statuscontrole. Bambu Studio blijft leidend voor slicing, voorbereiden en starten van prints."
      />
      <BambuPrintersContent data={data} />
    </AppShell>
  );
}

function BambuPrintersContent({ data }: { data: BambuPrintersData }) {
  const reachable = data.printers.filter((printer) => ["bereikbaar", "status_opgehaald"].includes(printer.last_status || ""));
  const missingAccess = data.printers.filter((printer) => !printer.has_access_code);
  const active = data.printers.filter((printer) => printer.active);
  const statusRead = data.printers.filter((printer) => printer.last_status === "status_opgehaald");

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doet deze koppeling?" description="Deze pagina leest alleen printerinformatie uit. De app zet geen LAN-only modus aan, start geen prints en verandert geen printerinstellingen.">
        <div className="grid gap-4 md:grid-cols-3">
          <WorkflowStep title="1. Bambu Studio blijft leidend" text="Blijf Bambu Studio gebruiken voor slicing, printvoorbereiding en het starten van prints." />
          <WorkflowStep title="2. Alleen meelezen" text="Verbinding testen en status ophalen zijn read-only controles vanaf de NAS naar de printer." />
          <WorkflowStep title="3. LAN-only niet verplicht" text="Zet LAN-only alleen aan als jij bewust cloudfuncties wilt uitschakelen. Deze app dwingt dat niet af." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Printers" value={data.printers.length} note="geregistreerd" />
        <MetricCard label="Actief" value={active.length} note="in gebruik" />
        <MetricCard label="Bereikbaar" value={reachable.length} note="laatste controle" tone={reachable.length ? "good" : "warning"} />
        <MetricCard label="Status gelezen" value={statusRead.length} note="MQTT-status" tone={statusRead.length ? "good" : "warning"} />
      </div>

      {missingAccess.length ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          {missingAccess.length} printer(s) missen nog een access code. Zonder access code kan de app geen status proberen op te halen, maar Bambu Studio blijft gewoon bruikbaar.
        </div>
      ) : null}

      <SectionCard title="Printers beheren" description="Gebruik 'Verbinding testen' voor netwerkbereik en 'Status ophalen' voor een read-only statuspoging. Geen van beide start een print.">
        <BambuPrinterManager printers={data.printers} />
      </SectionCard>
    </div>
  );
}

function WorkflowStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border-l-4 border-brand bg-slate-50 p-4">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  );
}
