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
  let data: BambuPrintersData | null = null;
  let error: string | null = null;
  try {
    data = await getBambuPrintersData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Bambu printers"
        description="Registreer je Bambu-printers en controleer veilig of ze via LAN bereikbaar zijn. Automatisch printen blijft uitgeschakeld."
      />
      {error || !data ? <SectionCard title="Bambu printers niet bereikbaar"><EmptyState title="Geen printerdata" description={error || "Geen data beschikbaar"} /></SectionCard> : <BambuPrintersContent data={data} />}
    </AppShell>
  );
}

function BambuPrintersContent({ data }: { data: BambuPrintersData }) {
  const reachable = data.printers.filter((printer) => printer.last_status === "bereikbaar");
  const missingAccess = data.printers.filter((printer) => !printer.has_access_code);
  const active = data.printers.filter((printer) => printer.active);

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Deze eerste Bambu-koppeling is bedoeld voor farmoverzicht en veilige LAN-controle. Printstart en slicing blijven buiten deze app.">
        <div className="grid gap-4 md:grid-cols-3">
          <WorkflowStep title="1. Printer toevoegen" text="Vul naam, model, IP-adres en eventueel access code in." />
          <WorkflowStep title="2. LAN testen" text="Controleer of de printerpoort bereikbaar is vanaf de server/NAS." />
          <WorkflowStep title="3. Later uitbreiden" text="Hierna kunnen we echte statusfeeds, wachtrijen en farmplanning toevoegen." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Printers" value={data.printers.length} note="geregistreerd" />
        <MetricCard label="Actief" value={active.length} note="in gebruik" />
        <MetricCard label="Bereikbaar" value={reachable.length} note="laatste test" tone={reachable.length ? "good" : "warning"} />
        <MetricCard label="Access code mist" value={missingAccess.length} note="nodig voor MQTT later" tone={missingAccess.length ? "warning" : "good"} />
      </div>

      <SectionCard title="Printers beheren" description="De statuscheck test alleen netwerkbereik. Er wordt niets naar de printer gestuurd dat een print start.">
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
