import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getBambuPrintersData } from "@/lib/api";
import {
  hasStatusMeasurement,
  isPrinting,
  lastMeasuredLabel,
  operationalState,
  progressLabel,
  progressValue,
  reachabilityLabel,
  remainingTimeLabel,
  taskLabel,
  temperatureLabel,
} from "@/lib/printerPresentation";
import type { BambuPrinter, BambuPrintersData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function BambuPrintersPage() {
  const data = await getBambuPrintersData().catch(() => ({ printers: [] }));
  return (
    <AppShell>
      <PageHeader
        title="Printers"
        description="Laatst gemeten printerstatus, voortgang en temperatuur. Ontbrekende metingen blijven herkenbaar als onbekend."
        actions={<a className="rounded-md border border-line px-4 py-2 text-sm font-bold text-slate-200 hover:border-brand" href="/bambu-printers/beheer">Printers beheren</a>}
      />
      <PrintersContent data={data} />
    </AppShell>
  );
}

function PrintersContent({ data }: { data: BambuPrintersData }) {
  const visiblePrinters = data.printers;
  const active = visiblePrinters.filter((printer) => printer.active);
  const measured = visiblePrinters.filter(hasStatusMeasurement);
  const printing = visiblePrinters.filter(isPrinting);
  const attention = visiblePrinters.filter((printer) => ["aandacht_nodig", "fout", "error", "pause"].some((status) => (printer.last_status || printer.printer_state || "").toLowerCase().includes(status)));
  const offline = visiblePrinters.filter((printer) => (printer.last_status || "").includes("offline"));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Printers" value={visiblePrinters.length} note="geregistreerd" />
        <MetricCard label="Ingeschakeld" value={active.length} note="actief in deze app" tone="good" />
        <MetricCard label="Status ontvangen" value={measured.length} note="met printermeting" />
        <MetricCard label="Print bezig" value={printing.length} note="lopende opdrachten" tone="warning" />
        <MetricCard label="Aandacht" value={attention.length} note="pauze/fout/controle" tone={attention.length ? "warning" : "good"} />
        <MetricCard label="Offline" value={offline.length} note="geen status" tone={offline.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Printergrid" description="Status en temperaturen komen uit de laatste printermeting. Bereikbaarheid is een afzonderlijke verbindingscontrole.">
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {visiblePrinters.map((printer) => <PrinterCard key={printer.id} printer={printer} />)}
        </div>
        {!visiblePrinters.length ? <EmptyState title="Nog geen printers" description="Voeg in printerbeheer de eerste printer toe om echte status te tonen." actionHref="/bambu-printers/beheer" actionLabel="Printer toevoegen" /> : null}
      </SectionCard>

    </div>
  );
}

function PrinterCard({ printer }: { printer: BambuPrinter }) {
  const state = operationalState(printer);
  const progress = progressValue(printer);
  const statusTone = statusClass(state, printer.last_status);

  return (
    <article className={`rounded-2xl border bg-panelSoft p-5 shadow-card ${statusTone.border}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xl font-black text-ink">{printer.name}</div>
          <div className="mt-1 text-sm font-semibold text-muted">{printer.model || "Onbekend model"} - {printer.location || "geen locatie"}</div>
        </div>
        <StatusBadge status={state} />
      </div>

      <div className="mt-5">
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-bold text-slate-200">{taskLabel(printer)}</span>
          <span className="text-muted">{progressLabel(printer)}</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-800">
          <div className={`h-full rounded-full ${statusTone.fill}`} style={{ width: `${progress ?? 0}%` }} />
        </div>
        <div className="mt-2 text-sm text-muted">{remainingTimeLabel(printer)}</div>
        <div className="mt-1 text-xs font-semibold text-muted">{lastMeasuredLabel(printer.last_seen_at)}</div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Small label="Filament in gebruik" value="Onbekend" />
        <Small label="Nozzle gemeten" value={temperatureLabel(printer.nozzle_temperature)} />
        <Small label="Bed gemeten" value={temperatureLabel(printer.bed_temperature)} />
        <Small label="Onderhoud" value="Niet geregistreerd" />
        <div className="col-span-2"><Small label="Bereikbaarheid" value={reachabilityLabel(printer.last_status)} /></div>
      </div>

      <div className="mt-5 flex justify-between gap-3">
        <span className="text-xs font-bold uppercase text-muted">{printer.host}:{printer.mqtt_port}</span>
        <a className="rounded-md border border-line px-3 py-2 text-sm font-black text-slate-200 hover:border-brand" href={`/bambu-printers/beheer#printer-${printer.id}`}>
          Beheren
        </a>
      </div>
    </article>
  );
}

function statusClass(state: string, lastStatus?: string | null) {
  const value = `${state} ${lastStatus || ""}`.toLowerCase();
  if (value.includes("error") || value.includes("fout")) {
    return { border: "border-red-400/30", fill: "bg-red-400" };
  }
  if (value.includes("pause") || value.includes("aandacht")) {
    return { border: "border-amber-400/30", fill: "bg-amber-400" };
  }
  if (value.includes("running") || value.includes("print")) {
    return { border: "border-sky-400/30", fill: "bg-sky-400" };
  }
  if (value.includes("offline")) {
    return { border: "border-slate-500/30", fill: "bg-slate-500" };
  }
  if (value.includes("onbekend") || value.includes("unknown") || value.includes("inactief")) {
    return { border: "border-slate-500/30", fill: "bg-slate-500" };
  }
  return { border: "border-emerald-400/30", fill: "bg-emerald-400" };
}

function Small({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-slate-950/25 p-3">
      <div className="text-[11px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
      <div className="mt-1 font-black text-ink">{value}</div>
    </div>
  );
}
