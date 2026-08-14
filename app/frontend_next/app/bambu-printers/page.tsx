import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getBambuPrintersData } from "@/lib/api";
import type { BambuPrinter, BambuPrintersData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function BambuPrintersPage() {
  const data = await getBambuPrintersData().catch(() => ({ printers: [] }));
  return (
    <AppShell>
      <PageHeader
        title="Printers"
        description="Actuele status, voortgang, temperatuur en onderhoudssignalen van je printfarm. Printbestanden open je vanuit Producten in Bambu Studio."
        actions={<a className="rounded-md border border-line px-4 py-2 text-sm font-bold text-slate-200 hover:border-brand" href="/bambu-printers/beheer">Printers beheren</a>}
      />
      <PrintersContent data={data} />
    </AppShell>
  );
}

function PrintersContent({ data }: { data: BambuPrintersData }) {
  const visiblePrinters = data.printers;
  const active = visiblePrinters.filter((printer) => printer.active);
  const printing = visiblePrinters.filter((printer) => ["RUNNING", "PRINTING", "bezig"].includes((printer.printer_state || "").toUpperCase()));
  const attention = visiblePrinters.filter((printer) => ["aandacht_nodig", "fout", "ERROR", "PAUSE"].some((status) => (printer.last_status || printer.printer_state || "").includes(status)));
  const offline = visiblePrinters.filter((printer) => (printer.last_status || "").includes("offline"));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Printers" value={visiblePrinters.length} note="geregistreerd" />
        <MetricCard label="Actief" value={active.length} note="beschikbaar in farm" tone="good" />
        <MetricCard label="Print bezig" value={printing.length} note="lopende opdrachten" tone="warning" />
        <MetricCard label="Aandacht" value={attention.length} note="pauze/fout/controle" tone={attention.length ? "warning" : "good"} />
        <MetricCard label="Offline" value={offline.length} note="geen status" tone={offline.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Printergrid" description="Elke kaart toont de operationele status die je in een printfarm snel wilt kunnen scannen.">
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {visiblePrinters.map((printer) => <PrinterCard key={printer.id} printer={printer} />)}
        </div>
        {!visiblePrinters.length ? <EmptyState title="Nog geen printers" description="Voeg in printerbeheer de eerste printer toe om echte status te tonen." actionHref="/bambu-printers/beheer" actionLabel="Printer toevoegen" /> : null}
      </SectionCard>

    </div>
  );
}

function PrinterCard({ printer }: { printer: BambuPrinter }) {
  const state = printer.printer_state || printer.last_status || "onbekend";
  const progress = Math.max(0, Math.min(Number(printer.print_progress || 0), 100));
  const statusTone = statusClass(state, printer.last_status);
  const remaining = progress > 0 ? `${Math.max(Math.round((100 - progress) * 2.4), 5)} min resterend` : "Geen actieve opdracht";

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
          <span className="font-bold text-slate-200">{printer.current_task || "Geen opdracht"}</span>
          <span className="text-muted">{progress}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-800">
          <div className={`h-full rounded-full ${statusTone.fill}`} style={{ width: `${progress}%` }} />
        </div>
        <div className="mt-2 text-sm text-muted">{remaining}</div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Small label="Filament" value={printer.current_task?.includes("Rood") ? "Rood PLA" : "PLA"} />
        <Small label="Nozzle" value={`${Math.round(Number(printer.nozzle_temperature || 0))}C`} />
        <Small label="Bed" value={`${Math.round(Number(printer.bed_temperature || 0))}C`} />
        <Small label="Onderhoud" value={statusTone.maintenance} />
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
    return { border: "border-red-400/30", fill: "bg-red-400", maintenance: "Fout" };
  }
  if (value.includes("pause") || value.includes("aandacht")) {
    return { border: "border-amber-400/30", fill: "bg-amber-400", maintenance: "Controle" };
  }
  if (value.includes("running") || value.includes("print")) {
    return { border: "border-sky-400/30", fill: "bg-sky-400", maintenance: "OK" };
  }
  if (value.includes("offline")) {
    return { border: "border-slate-500/30", fill: "bg-slate-500", maintenance: "Offline" };
  }
  return { border: "border-emerald-400/30", fill: "bg-emerald-400", maintenance: "OK" };
}

function Small({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-slate-950/25 p-3">
      <div className="text-[11px] font-black uppercase tracking-[.12em] text-muted">{label}</div>
      <div className="mt-1 font-black text-ink">{value}</div>
    </div>
  );
}
