"use client";

import { FormEvent, useEffect, useState } from "react";
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
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-50 p-4" onSubmit={createPrinter}>
        <h3 className="font-bold text-ink">Bambu-printer toevoegen</h3>
        <p className="mt-1 text-sm text-muted">Gebruik het lokale IP-adres van de printer. De access code wordt opgeslagen, maar niet teruggetoond.</p>
        <PrinterFields draft={newDraft} onChange={updateNew} />
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busyKey === "new"} type="submit">
            {busyKey === "new" ? "Aanmaken..." : "Printer aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {items.length ? items.map((printer) => {
          const draft = drafts[printer.id] || draftFromPrinter(printer);
          return (
            <details className="rounded-lg border border-line bg-white p-4 shadow-card" key={printer.id}>
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
                  <button className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60" disabled={busyKey !== null} onClick={() => testConnection(printer.id)} type="button">
                    {busyKey === `test-${printer.id}` ? "Testen..." : "Verbinding testen"}
                  </button>
                  <button className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60" disabled={busyKey !== null} onClick={() => refreshStatus(printer.id)} type="button">
                    {busyKey === `status-${printer.id}` ? "Ophalen..." : "Status ophalen"}
                  </button>
                  <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busyKey !== null} onClick={() => savePrinter(printer.id)} type="button">
                    {busyKey === `save-${printer.id}` ? "Opslaan..." : "Printer opslaan"}
                  </button>
                </div>
              </div>
            </details>
          );
        }) : (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            Nog geen Bambu-printers. Voeg hierboven je eerste printer toe.
          </div>
        )}
      </div>
    </div>
  );
}

function PrinterFields({ draft, onChange }: { draft: PrinterDraft; onChange: (field: keyof PrinterDraft, value: string | boolean) => void }) {
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <TextField label="Naam" value={draft.name} onChange={(value) => onChange("name", value)} placeholder="Bijv. X1C links" />
      <TextField label="Model" value={draft.model} onChange={(value) => onChange("model", value)} placeholder="X1C, P1S, A1 mini" />
      <TextField label="IP-adres / host" value={draft.host} onChange={(value) => onChange("host", value)} placeholder="Bijv. 10.5.1.42" />
      <TextField label="MQTT-poort" value={draft.mqtt_port} onChange={(value) => onChange("mqtt_port", value)} inputMode="numeric" />
      <TextField label="Serienummer voor status" value={draft.serial_number} onChange={(value) => onChange("serial_number", value)} placeholder="Nodig voor MQTT-status" />
      <TextField label="Locatie" value={draft.location} onChange={(value) => onChange("location", value)} placeholder="Bijv. Rek printerfarm" />
      <TextField label="Access code" value={draft.access_code} onChange={(value) => onChange("access_code", value)} placeholder="Leeg laten om bestaande code te behouden" type="password" />
      <label className="flex items-center gap-3 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold">
        <input checked={draft.active} onChange={(event) => onChange("active", event.target.checked)} type="checkbox" />
        Printer actief
      </label>
    </div>
  );
}

function StatusValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-50 px-3 py-2">
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
  inputMode,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "decimal";
  type?: "text" | "password";
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
    </label>
  );
}
