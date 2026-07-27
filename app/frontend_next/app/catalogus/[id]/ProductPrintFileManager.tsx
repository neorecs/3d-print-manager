"use client";

import { ChangeEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import type { BambuPrinter, Product } from "@/lib/types";

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

export function ProductPrintFileManager({ product, printers }: { product: Product; printers: BambuPrinter[] }) {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState<"preflight" | "start" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPrinterId, setSelectedPrinterId] = useState(printers[0]?.id ? String(printers[0].id) : "");
  const [plate, setPlate] = useState("Metadata/plate_1.gcode");
  const [useAms, setUseAms] = useState(false);
  const [bedLeveling, setBedLeveling] = useState(true);
  const [layerInspect, setLayerInspect] = useState(true);
  const [confirmationText, setConfirmationText] = useState("");
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);

  async function uploadPrintFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`/api/products/${product.id}/print-file/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Printbestand uploaden is mislukt");
      setMessage(data?.message || "Printbestand gekoppeld aan product.");
      setPreflight(null);
      setConfirmationText("");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printbestand uploaden is mislukt");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  const filename = product.print_file_path?.split("/").pop() || null;
  const selectedPrinter = printers.find((printer) => String(printer.id) === selectedPrinterId);
  const printerFilePath = filename ? `file:///sdcard/${encodeURIComponent(filename)}` : "";
  const confirmationOk = confirmationText.trim().toUpperCase() === "START PRINT";
  const startBlockedReason = !product.print_file_path
    ? "Koppel eerst een printbestand aan dit product."
    : !selectedPrinterId
      ? "Kies eerst een printer."
      : !preflight
        ? "Klik eerst op Preflight controleren. Daarna wordt Print starten actief als alle controles goed zijn."
        : !preflight.ok
          ? "Preflight blokkeert printstart. Los de rode controles op en controleer opnieuw."
          : !confirmationOk
            ? "Typ START PRINT als bevestiging om de knop actief te maken."
            : null;
  const canStart = !startBlockedReason;

  function startPayload() {
    return {
      file_path: printerFilePath,
      local_upload_path: product.print_file_path || null,
      plate: plate.trim() || "Metadata/plate_1.gcode",
      use_ams: useAms,
      timelapse: false,
      flow_cali: false,
      bed_leveling: bedLeveling,
      layer_inspect: layerInspect,
      vibration_cali: false,
      confirmation_text: confirmationText,
    };
  }

  async function runPreflight() {
    if (!selectedPrinterId || !product.print_file_path || !printerFilePath) return;
    setBusy("preflight");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${selectedPrinterId}/print-preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(startPayload()),
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
    if (!canStart) return;
    setBusy("start");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/bambu/printers/${selectedPrinterId}/start-print`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(startPayload()),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = data?.detail;
        throw new Error(typeof detail === "string" ? detail : detail?.message || "Printstart mislukt");
      }
      setMessage(data.message || "Printstart verzonden.");
      setConfirmationText("");
      setPreflight(null);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printstart mislukt");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <div className="rounded-lg border border-line bg-slate-950/25 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="font-bold text-ink">Standaard printbestand</h3>
            <p className="mt-1 text-sm leading-6 text-muted">
              Koppel hier het printklare Bambu Studio bestand voor dit product. Varianten gebruiken ditzelfde bestand; kleur en materiaal regel je via planning, filament en printerinstellingen.
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-300">
              {filename ? `Gekoppeld: ${filename}` : "Nog geen printbestand gekoppeld."}
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5">
            {uploading ? "Uploaden..." : filename ? "Bestand vervangen" : "Printbestand kiezen"}
            <input accept=".gcode.3mf" className="sr-only" disabled={uploading} onChange={uploadPrintFile} type="file" />
          </label>
        </div>
      </div>

      <div className="rounded-lg border border-line bg-slate-950/25 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="font-bold text-ink">Print dit product</h3>
            <p className="mt-1 text-sm leading-6 text-muted">
              Gebruik het gekoppelde productbestand om eerst een preflight te draaien. Bij printstart uploadt de app het bestand naar de printer en stuurt daarna het LAN/MQTT startcommando.
            </p>
            {selectedPrinter ? <p className="mt-2 text-xs font-bold text-slate-400">Gekozen printer: {selectedPrinter.name} ({selectedPrinter.host})</p> : null}
          </div>
          <StatusBadge status={product.print_file_path ? "bestand gekoppeld" : "bestand ontbreekt"} />
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Printer</span>
            <select
              className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
              disabled={!printers.length}
              onChange={(event) => {
                setSelectedPrinterId(event.target.value);
                setPreflight(null);
              }}
              value={selectedPrinterId}
            >
              {printers.length ? printers.map((printer) => (
                <option key={printer.id} value={printer.id}>{printer.name} - {printer.host}</option>
              )) : <option value="">Geen printer beschikbaar</option>}
            </select>
          </label>
          <TextField label="Plate/gcode-pad in 3MF" value={plate} onChange={(value) => { setPlate(value); setPreflight(null); }} />
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <Option label="AMS gebruiken" checked={useAms} onChange={(value) => { setUseAms(value); setPreflight(null); }} />
          <Option label="Bed leveling" checked={bedLeveling} onChange={(value) => { setBedLeveling(value); setPreflight(null); }} />
          <Option label="Layer inspect" checked={layerInspect} onChange={(value) => { setLayerInspect(value); setPreflight(null); }} />
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5 disabled:opacity-60"
            disabled={busy !== null || !selectedPrinterId || !product.print_file_path}
            onClick={runPreflight}
            type="button"
          >
            {busy === "preflight" ? "Controleren..." : "Preflight controleren"}
          </button>
          <a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5" href="/bambu-printers">
            Printers beheren
          </a>
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
          <TextField label="Bevestigingstekst" value={confirmationText} onChange={setConfirmationText} placeholder="Typ START PRINT" />
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 hover:bg-brand/90 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
            disabled={busy !== null || !canStart}
            onClick={startPrint}
            type="button"
            title={startBlockedReason || "Klaar om printstart te verzenden"}
          >
            {busy === "start" ? "Start verzenden..." : "Print starten"}
          </button>
        </div>
        <div
          className={`mt-3 rounded-lg border px-3 py-2 text-sm font-semibold ${
            startBlockedReason
              ? "border-amber-400/25 bg-amber-400/10 text-amber-100"
              : "border-emerald-400/25 bg-emerald-400/10 text-emerald-100"
          }`}
        >
          {startBlockedReason || "Alles staat klaar. Je kunt de printstart nu verzenden."}
        </div>
      </div>
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

function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}
