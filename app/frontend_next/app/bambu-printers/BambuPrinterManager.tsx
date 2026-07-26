"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import type { BambuPrinter } from "@/lib/types";

type PrinterDraft = {
  name: string;
  model: string;
  serial_number: string;
  host: string;
  mqtt_port: string;
  access_code: string;
  connection_mode: string;
  location: string;
  active: boolean;
};

type PrintStartDraft = {
  file_path: string;
  local_upload_path: string;
  plate: string;
  use_ams: boolean;
  timelapse: boolean;
  flow_cali: boolean;
  bed_leveling: boolean;
  layer_inspect: boolean;
  vibration_cali: boolean;
  confirmation_text: string;
};

type PreflightCheck = {
  name: string;
  ok: boolean;
  message: string;
  level: "error" | "warning";
};

type PreflightResult = {
  ok: boolean;
  message: string;
  confirmation_required: string;
  checks: PreflightCheck[];
};

function emptyDraft(): PrinterDraft {
  return {
    name: "",
    model: "",
    serial_number: "",
    host: "",
    mqtt_port: "8883",
    access_code: "",
    connection_mode: "lan",
    location: "",
    active: true,
  };
}

function emptyPrintStartDraft(): PrintStartDraft {
  return {
    file_path: "file:///sdcard/",
    local_upload_path: "",
    plate: "Metadata/plate_1.gcode",
    use_ams: false,
    timelapse: false,
    flow_cali: false,
    bed_leveling: true,
    layer_inspect: true,
    vibration_cali: false,
    confirmation_text: "",
  };
}

function draftFromPrinter(printer: BambuPrinter): PrinterDraft {
  return {
    name: printer.name || "",
    model: printer.model || "",
    serial_number: printer.serial_number || "",
    host: printer.host || "",
    mqtt_port: String(printer.mqtt_port || 8883),
    access_code: "",
    connection_mode: printer.connection_mode || "lan",
    location: printer.location || "",
    active: printer.active !== false,
  };
}

function numberOrDefault(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function formatPercent(value?: number | null) {
  return typeof value === "number" ? `${value}%` : "onbekend";
}

function formatTemperature(value?: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)} °C` : "onbekend";
}

function formatDateTime(value?: string | null) {
  if (!value) return "nog niet gezien";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("nl-NL");
}

function toPayload(draft: PrinterDraft) {
  const payload: Record<string, string | number | boolean | null> = {
    name: draft.name.trim(),
    model: draft.model || null,
    serial_number: draft.serial_number || null,
    host: draft.host.trim(),
    mqtt_port: numberOrDefault(draft.mqtt_port, 8883),
    connection_mode: draft.connection_mode || "lan",
    location: draft.location || null,
    active: draft.active,
  };
  if (draft.access_code.trim()) {
    payload.access_code = draft.access_code.trim();
  }
  return payload;
}

export function BambuPrinterManager({ printers }: { printers: BambuPrinter[] }) {
  const [items, setItems] = useState<BambuPrinter[]>(printers);
  const [newDraft, setNewDraft] = useState<PrinterDraft>(() => emptyDraft());
  const [drafts, setDrafts] = useState<Record<number, PrinterDraft>>(() => Object.fromEntries(printers.map((printer) => [printer.id, draftFromPrinter(printer)])));
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadPrinters() {
    const response = await fetch("/api/bambu/printers", { cache: "no-store" });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(data?.detail || "Bambu-printers konden niet worden geladen");
    setItems(data);
    setDrafts(Object.fromEntries(data.map((printer: BambuPrinter) => [printer.id, draftFromPrinter(printer)])));
  }

  useEffect(() => {
    loadPrinters().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Bambu-printers konden niet worden geladen");
    });
  }, []);

  function updateNew(field: keyof PrinterDraft, value: string | boolean) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateDraft(id: number, field: keyof PrinterDraft, value: string | boolean) {
    setDrafts((current) => ({ ...current, [id]: { ...current[id], [field]: value } }));
  }

  async function createPrinter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("new");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/bambu/printers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(newDraft)),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Printer kon niet worden aangemaakt");
      setNewDraft(emptyDraft());
      setMessage("Printer aangemaakt.");
      await loadPrinters();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printer opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function savePrinter(id: number) {
    setBusyKey(`save-${id}`);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(drafts[id])),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Printer kon niet worden opgeslagen");
      setMessage("Printer opgeslagen.");
      await loadPrinters();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printer opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function testConnection(id: number) {
    setBusyKey(`test-${id}`);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${id}/test-connection`, { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Verbindingstest is mislukt");
      setMessage(data?.status_message || "Verbindingstest uitgevoerd.");
      await loadPrinters();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verbindingstest is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function refreshStatus(id: number) {
    setBusyKey(`status-${id}`);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${id}/refresh-status`, { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Status ophalen is mislukt");
      setMessage(data?.status_message || "Printerstatus opgehaald.");
      await loadPrinters();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Status ophalen is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={createPrinter}>
        <h3 className="font-bold text-ink">Bambu-printer toevoegen</h3>
        <p className="mt-1 text-sm text-muted">
          Gebruik het lokale IP-adres van de printer. De access code wordt versleuteld opgeslagen en niet teruggetoond. De site gebruikt LAN-bediening voor status en handmatige printstart; Bambu Studio blijft daarnaast gewoon bruikbaar.
        </p>
        <PrinterFields draft={newDraft} onChange={updateNew} />
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === "new"} type="submit">
            {busyKey === "new" ? "Aanmaken..." : "Printer aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {items.length ? items.map((printer) => {
          const draft = drafts[printer.id] || draftFromPrinter(printer);
          return (
            <details className="rounded-lg border border-line bg-panelSoft p-4 shadow-card" key={printer.id}>
              <summary className="cursor-pointer list-none">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="font-bold text-ink">{printer.name}</div>
                    <p className="mt-1 text-sm text-muted">
                      {printer.model || "model onbekend"} - {printer.host}:{printer.mqtt_port} - {printer.location || "geen locatie"}
                    </p>
                    {printer.status_message ? <p className="mt-2 text-sm text-muted">{printer.status_message}</p> : null}
                    <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                      <StatusValue label="Status" value={printer.printer_state || "onbekend"} />
                      <StatusValue label="Voortgang" value={formatPercent(printer.print_progress)} />
                      <StatusValue label="Taak" value={printer.current_task || "geen actieve taak"} />
                      <StatusValue label="Nozzle" value={formatTemperature(printer.nozzle_temperature)} />
                      <StatusValue label="Bed" value={formatTemperature(printer.bed_temperature)} />
                      <StatusValue label="Laatst gezien" value={formatDateTime(printer.last_seen_at)} />
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={printer.last_status || "onbekend"} />
                    <StatusBadge status={printer.has_access_code ? "access code opgeslagen" : "access code mist"} />
                  </div>
                </div>
              </summary>
              <div className="mt-4 border-t border-line pt-4">
                <PrinterFields draft={draft} onChange={(field, value) => updateDraft(printer.id, field, value)} />
                <div className="mt-4 flex flex-wrap justify-end gap-3">
                  <button className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5 disabled:opacity-60" disabled={busyKey !== null} onClick={() => testConnection(printer.id)} type="button">
                    {busyKey === `test-${printer.id}` ? "Testen..." : "Verbinding testen"}
                  </button>
                  <button className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5 disabled:opacity-60" disabled={busyKey !== null} onClick={() => refreshStatus(printer.id)} type="button">
                    {busyKey === `status-${printer.id}` ? "Ophalen..." : "Status ophalen"}
                  </button>
                  <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey !== null} onClick={() => savePrinter(printer.id)} type="button">
                    {busyKey === `save-${printer.id}` ? "Opslaan..." : "Printer opslaan"}
                  </button>
                </div>
                <BambuPrintStartPanel printer={printer} onRefresh={loadPrinters} />
              </div>
            </details>
          );
        }) : (
          <div className="rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-800">
            Nog geen Bambu-printers. Voeg hierboven je eerste printer toe.
          </div>
        )}
      </div>
    </div>
  );
}

function BambuPrintStartPanel({ printer, onRefresh }: { printer: BambuPrinter; onRefresh: () => Promise<void> }) {
  const [draft, setDraft] = useState<PrintStartDraft>(() => emptyPrintStartDraft());
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const [busy, setBusy] = useState<"upload" | "preflight" | "start" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof PrintStartDraft, value: string | boolean) {
    setDraft((current) => ({
      ...current,
      [field]: value,
      local_upload_path: field === "file_path" ? "" : current.local_upload_path,
    }));
    if (field !== "confirmation_text") setPreflight(null);
  }

  function payload() {
    return {
      file_path: draft.file_path.trim(),
      local_upload_path: draft.local_upload_path || null,
      plate: draft.plate.trim() || "Metadata/plate_1.gcode",
      use_ams: draft.use_ams,
      timelapse: draft.timelapse,
      flow_cali: draft.flow_cali,
      bed_leveling: draft.bed_leveling,
      layer_inspect: draft.layer_inspect,
      vibration_cali: draft.vibration_cali,
      confirmation_text: draft.confirmation_text,
    };
  }

  async function uploadPrintFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("upload");
    setMessage(null);
    setError(null);
    setPreflight(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`/api/bambu/printers/${printer.id}/print-files/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Printbestand uploaden is mislukt");
      setDraft((current) => ({
        ...current,
        file_path: data.file_path || current.file_path,
        local_upload_path: data.local_upload_path || "",
        confirmation_text: "",
      }));
      setMessage(data.message || "Printbestand geupload. Bij printstart wordt het bestand naar de printer verstuurd.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printbestand uploaden is mislukt");
    } finally {
      setBusy(null);
      event.target.value = "";
    }
  }

  async function runPreflight() {
    setBusy("preflight");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${printer.id}/print-preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload()),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail?.message || data?.detail || "Preflight mislukt");
      setPreflight(data);
      setMessage(data.message || "Preflight uitgevoerd.");
    } catch (caught) {
      setPreflight(null);
      setError(caught instanceof Error ? caught.message : "Preflight mislukt");
    } finally {
      setBusy(null);
    }
  }

  async function startPrint() {
    setBusy("start");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${printer.id}/start-print`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload()),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = data?.detail;
        throw new Error(typeof detail === "string" ? detail : detail?.message || "Printstart mislukt");
      }
      setMessage(data.message || "Printstart verzonden.");
      setDraft((current) => ({ ...current, confirmation_text: "" }));
      await onRefresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printstart mislukt");
    } finally {
      setBusy(null);
    }
  }

  const canStart = Boolean(preflight?.ok && draft.confirmation_text.trim().toUpperCase() === "START PRINT");

  return (
    <div className="mt-5 rounded-xl border border-amber-400/25 bg-amber-400/5 p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h4 className="font-black text-ink">Print starten vanaf printer/SD</h4>
          <p className="mt-1 text-sm leading-6 text-muted">
            Gebruik dit voor printfarm-opdrachten die al door Bambu Studio zijn voorbereid. Voor losse of persoonlijke prints kun je Bambu Studio gewoon blijven gebruiken.
          </p>
        </div>
        <StatusBadge status="handmatige bevestiging vereist" />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <TextField
          help="Dit moet een volledig 3MF-projectbestand zijn dat al op de printer/SD staat. Alleen file:///sdcard/ is nog geen geldig bestand."
          label="SD-bestandspad"
          value={draft.file_path}
          onChange={(value) => update("file_path", value)}
          placeholder="file:///sdcard/bestand.gcode.3mf"
        />
        <TextField label="Plate/gcode-pad in 3MF" value={draft.plate} onChange={(value) => update("plate", value)} placeholder="Metadata/plate_1.gcode" />
      </div>

      <div className="mt-4 rounded-lg border border-line bg-slate-950/25 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h5 className="font-black text-ink">3MF-bestand via de site gebruiken</h5>
            <p className="mt-1 text-sm leading-6 text-muted">
              Upload hier een door Bambu Studio voorbereid .gcode.3mf bestand. Bij printstart stuurt de site dit bestand eerst via FTPS naar de printer en start daarna de print via LAN/MQTT.
            </p>
            {draft.local_upload_path ? <p className="mt-2 text-xs font-bold text-emerald-300">Bestand klaar in de app: {draft.local_upload_path}</p> : null}
          </div>
          <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5">
            {busy === "upload" ? "Uploaden..." : "Printbestand kiezen"}
            <input accept=".gcode.3mf" className="sr-only" disabled={busy !== null} onChange={uploadPrintFile} type="file" />
          </label>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Option label="AMS gebruiken" checked={draft.use_ams} onChange={(value) => update("use_ams", value)} />
        <Option label="Timelapse" checked={draft.timelapse} onChange={(value) => update("timelapse", value)} />
        <Option label="Flow calibration" checked={draft.flow_cali} onChange={(value) => update("flow_cali", value)} />
        <Option label="Bed leveling" checked={draft.bed_leveling} onChange={(value) => update("bed_leveling", value)} />
        <Option label="Layer inspect" checked={draft.layer_inspect} onChange={(value) => update("layer_inspect", value)} />
        <Option label="Vibration calibration" checked={draft.vibration_cali} onChange={(value) => update("vibration_cali", value)} />
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5 disabled:opacity-60" disabled={busy !== null} onClick={runPreflight} type="button">
          {busy === "preflight" ? "Controleren..." : "Preflight controleren"}
        </button>
      </div>

      {preflight ? (
        <div className="mt-4 space-y-2">
          {preflight.checks.map((check) => (
            <div className={`rounded-lg border px-3 py-2 text-sm ${check.ok ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100" : check.level === "warning" ? "border-amber-400/25 bg-amber-400/10 text-amber-100" : "border-red-400/25 bg-red-400/10 text-red-100"}`} key={check.name}>
              <span className="font-black">{check.ok ? "OK" : check.level === "warning" ? "Let op" : "Blokkeert"} - {check.name}:</span> {check.message}
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-300">Bevestigingstekst</span>
          <input
            className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
            onChange={(event) => update("confirmation_text", event.target.value)}
            placeholder="Typ START PRINT"
            value={draft.confirmation_text}
          />
        </label>
        <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50" disabled={busy !== null || !canStart} onClick={startPrint} type="button">
          {busy === "start" ? "Start verzenden..." : "Print starten"}
        </button>
      </div>

      {message ? <div className="mt-4 rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-200">{message}</div> : null}
      {error ? <div className="mt-4 rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-200">{error}</div> : null}
    </div>
  );
}

function Option({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm font-semibold text-ink">
      <input checked={checked} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
      {label}
    </label>
  );
}

function PrinterFields({ draft, onChange }: { draft: PrinterDraft; onChange: (field: keyof PrinterDraft, value: string | boolean) => void }) {
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <TextField label="Naam" value={draft.name} onChange={(value) => onChange("name", value)} placeholder="Bijv. X1C links" />
      <TextField label="Model" value={draft.model} onChange={(value) => onChange("model", value)} placeholder="X1C, P1S, A1 mini" />
      <TextField label="IP-adres / host" value={draft.host} onChange={(value) => onChange("host", value)} placeholder="Bijv. 10.5.1.42" />
      <TextField label="MQTT-poort" value={draft.mqtt_port} onChange={(value) => onChange("mqtt_port", value)} inputMode="numeric" />
      <TextField label="Serienummer voor status en printstart" value={draft.serial_number} onChange={(value) => onChange("serial_number", value)} placeholder="Nodig voor status en printstart" />
      <TextField label="Locatie" value={draft.location} onChange={(value) => onChange("location", value)} placeholder="Bijv. Rek printerfarm" />
      <TextField label="Access code" value={draft.access_code} onChange={(value) => onChange("access_code", value)} placeholder="Leeg laten om bestaande code te behouden" type="password" />
      <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink font-semibold">
        <input checked={draft.active} onChange={(event) => onChange("active", event.target.checked)} type="checkbox" />
        Printer actief
      </label>
    </div>
  );
}

function StatusValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-panelSoft px-3 py-2">
      <div className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 truncate font-semibold text-ink">{value}</div>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  help,
  inputMode,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  help?: string;
  inputMode?: "text" | "numeric" | "decimal";
  type?: "text" | "password";
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
      {help ? <span className="block text-xs font-semibold leading-5 text-muted">{help}</span> : null}
    </label>
  );
}
