"use client";

import { ChangeEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import type { BambuPrinter, Product, ProductVariant } from "@/lib/types";

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

export function ProductPrintFileManager({ product, variants, printers }: { product: Product; variants: ProductVariant[]; printers: BambuPrinter[] }) {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState<"studio" | "preflight" | "start" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPrinterId, setSelectedPrinterId] = useState(printers.find((printer) => printer.active)?.id ? String(printers.find((printer) => printer.active)?.id) : "");
  const [plate, setPlate] = useState("Metadata/plate_1.gcode");
  const [useAms, setUseAms] = useState(false);
  const [bedLeveling, setBedLeveling] = useState(true);
  const [layerInspect, setLayerInspect] = useState(true);
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const [printerItems, setPrinterItems] = useState(printers);
  const [selectedVariantId, setSelectedVariantId] = useState(variants.find((variant) => variant.active !== false)?.id ? String(variants.find((variant) => variant.active !== false)?.id) : "");

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
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printbestand uploaden is mislukt");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function openInBambuStudio() {
    if (!product.print_file_path || !selectedPrinterId || !selectedVariantId) return;
    setBusy("studio");
    setMessage(null);
    setError(null);
    try {
      const statusResponse = await fetch(`/api/bambu/printers/${selectedPrinterId}/refresh-status`, { method: "POST" });
      const refreshedPrinter = await statusResponse.json().catch(() => null);
      if (!statusResponse.ok) throw new Error(refreshedPrinter?.detail || "Printer- en AMS-status ophalen is mislukt");
      setPrinterItems((current) => current.map((printer) => printer.id === refreshedPrinter.id ? refreshedPrinter : printer));

      const response = await fetch(`/api/products/${product.id}/print-file/open-in-bambu-studio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variant_id: Number(selectedVariantId), printer_id: Number(selectedPrinterId) }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.launcher_url) {
        throw new Error(data?.detail || "De lokale Bambu-koppeling kon niet worden gestart");
      }
      const slot = data.preparation?.recommended_slot;
      const warnings = Array.isArray(data.preparation?.warnings) ? data.preparation.warnings : [];
      setMessage([
        `${data.preparation?.printer_name || "Printer"} voorbereid${slot ? ` met ${slot.label} (${slot.material})` : "; kies het filament handmatig in Bambu Studio"}.`,
        ...warnings,
      ].join(" "));
      window.location.href = data.launcher_url;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Bambu Studio kon niet worden geopend");
    } finally {
      setBusy(null);
    }
  }

  const filename = product.print_file_path?.split("/").pop() || null;
  const selectedPrinter = printerItems.find((printer) => String(printer.id) === selectedPrinterId);
  const selectedVariant = variants.find((variant) => String(variant.id) === selectedVariantId);
  const startBlockedReason = !product.print_file_path
    ? "Koppel eerst een printbestand aan dit product."
    : !selectedPrinterId
      ? "Kies eerst een printer."
      : null;
  const canStart = !startBlockedReason;

  function startPayload() {
    return {
      local_upload_path: product.print_file_path,
      plate: plate.trim() || "Metadata/plate_1.gcode",
      use_ams: useAms,
      timelapse: false,
      flow_cali: false,
      bed_leveling: bedLeveling,
      layer_inspect: layerInspect,
      vibration_cali: false,
      confirmation_text: "START PRINT",
    };
  }

  async function runPreflight() {
    if (!selectedPrinterId || !product.print_file_path) return;
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
    setBusy("preflight");
    setMessage(null);
    setError(null);
    try {
      const preflightResponse = await fetch(`/api/bambu/printers/${selectedPrinterId}/print-preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(startPayload()),
      });
      const preflightData = await preflightResponse.json().catch(() => null);
      if (!preflightResponse.ok) throw new Error(preflightData?.detail?.message || preflightData?.detail || "Preflight mislukt");
      setPreflight(preflightData);
      if (!preflightData.ok) {
        setError("Controle blokkeert printstart. Los de meldingen hieronder op en probeer opnieuw.");
        return;
      }

      setBusy("start");
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
          <div className="flex flex-wrap gap-2">
            {product.print_file_path ? (
              <button
                className="inline-flex items-center justify-center rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 hover:bg-brand/90"
                disabled={busy !== null || !selectedPrinterId || !selectedVariantId}
                onClick={openInBambuStudio}
                type="button"
              >
                {busy === "studio" ? "Bambu Studio openen..." : "Open in Bambu Studio"}
              </button>
            ) : null}
            <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5">
              {uploading ? "Uploaden..." : filename ? "Bestand vervangen" : "Printbestand kiezen"}
              <input accept=".gcode.3mf" className="sr-only" disabled={uploading} onChange={uploadPrintFile} type="file" />
            </label>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-brand/30 bg-brand/5 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-wide text-brand">Aanbevolen cloudworkflow</p>
            <h3 className="mt-1 text-lg font-bold text-ink">Printen via Bambu Studio</h3>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
              Hiermee blijven Bambu Studio, Bambu Handy en Bambu Cloud normaal beschikbaar. De manager levert het juiste voorbereide bestand; Bambu Studio verstuurt de print.
            </p>
          </div>
          <StatusBadge status={product.print_file_path ? "klaar" : "bestand ontbreekt"} />
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <WorkflowStep number="1" title="Installeer eenmalig" description="Installeer op deze Windows-computer de veilige koppeling met Bambu Studio." />
          <WorkflowStep number="2" title="Open het bestand" description="De koppeling haalt het beveiligde bestand op en opent het lokaal in Bambu Studio, zonder websitewaarschuwing." />
          <WorkflowStep number="3" title="Print plate" description="Start de opdracht vanuit Bambu Studio. Verwerk daarna het resultaat in Printplanning." />
        </div>
        <div className="mt-4 grid gap-4 rounded-md border border-line bg-slate-950/35 p-4 lg:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Productvariant</span>
            <select
              className="w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
              onChange={(event) => setSelectedVariantId(event.target.value)}
              value={selectedVariantId}
            >
              {variants.filter((variant) => variant.active !== false).map((variant) => (
                <option key={variant.id} value={variant.id}>
                  {variant.variant_name || variant.sku || `Variant ${variant.id}`} - {variant.material || "materiaal ontbreekt"} / {variant.color || "kleur ontbreekt"}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Printer</span>
            <select
              className="w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
              onChange={(event) => setSelectedPrinterId(event.target.value)}
              value={selectedPrinterId}
            >
              {printerItems.filter((printer) => printer.active).map((printer) => (
                <option key={printer.id} value={printer.id}>{printer.name} - {printer.model || "model onbekend"}</option>
              ))}
            </select>
          </label>
          <div className="lg:col-span-2">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Beschikbare AMS-sleuven</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {selectedPrinter?.ams_slots?.length ? selectedPrinter.ams_slots.map((slot) => {
                const materialMatch = selectedVariant?.material?.trim().toLowerCase() === slot.material.trim().toLowerCase();
                return (
                  <span className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-bold ${materialMatch ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100" : "border-line bg-slate-950 text-slate-400"}`} key={`${slot.ams_id}-${slot.tray_id}`}>
                    <span className="h-3 w-3 rounded-full border border-white/30" style={{ backgroundColor: slot.color_hex || "#64748b" }} />
                    {slot.label}: {slot.material}{slot.remaining_percent != null ? ` (${slot.remaining_percent}%)` : ""}
                  </span>
                );
              }) : <span className="text-sm text-amber-200">De AMS-inhoud wordt automatisch opgehaald zodra je Bambu Studio opent.</span>}
            </div>
          </div>
          <div className="lg:col-span-2 rounded-md border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
            De manager controleert het printermodel en kiest waar mogelijk automatisch de printer en AMS-sleuf met passend materiaal en kleur. Ontbreekt die rol, dan opent het bestand alsnog en kies je het filament handmatig in Bambu Studio. Bevestig voor verzending nog de fysieke printer <strong>{selectedPrinter?.name || ""}</strong>.
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          {product.print_file_path ? (
            <button
              className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 hover:bg-brand/90 disabled:opacity-60"
              disabled={busy !== null || !selectedPrinterId || !selectedVariantId}
              onClick={openInBambuStudio}
              type="button"
            >
              {busy === "studio" ? "Bambu Studio openen..." : "Open direct in Bambu Studio"}
            </button>
          ) : (
            <span className="rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-2 text-sm font-bold text-amber-100">Upload eerst een printbestand</span>
          )}
          <a
            className="rounded-md border border-brand/40 bg-brand/10 px-4 py-2 text-sm font-bold text-brand hover:bg-brand/15"
            download
            href="/downloads/Installeer-Bambu-koppeling.cmd"
          >
            Windows-koppeling installeren
          </a>
          <a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5" href="/printplanning">
            Naar printplanning
          </a>
          {product.print_file_path ? (
            <a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5" download href={`/api/products/${product.id}/print-file/download`}>
              Alleen downloaden
            </a>
          ) : null}
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-400">Eenmalig per Windows-computer installeren. De launcher accepteert uitsluitend tijdelijke printbestanden van jouw eigen 3D Print Manager.</p>
      </div>

      <details className="rounded-lg border border-line bg-slate-950/25">
        <summary className="cursor-pointer list-none p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-ink">Directe LAN-printstart (geavanceerd)</h3>
              <p className="mt-1 text-sm text-muted">Alleen gebruiken bij een printer die bewust voor directe LAN-bediening is ingericht.</p>
            </div>
            <span className="text-sm font-bold text-slate-400">Instellingen tonen</span>
          </div>
        </summary>
        <div className="border-t border-line p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="font-bold text-ink">Direct naar printer sturen</h3>
            <p className="mt-1 text-sm leading-6 text-muted">
              De app controleert de printer, uploadt het bestand en stuurt het LAN/MQTT-startcommando. Dit is niet de aanbevolen route zolang je Bambu Cloud en Handy wilt behouden.
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
            {busy === "preflight" ? "Controleren..." : "Alleen controleren"}
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
          <div className="rounded-lg border border-line bg-slate-950/35 px-3 py-2 text-sm leading-6 text-muted">
            <span className="font-black text-ink">Veilige start:</span> bij klikken op Print starten voert de app automatisch eerst de controle uit.
          </div>
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 hover:bg-brand/90 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
            disabled={busy !== null || !canStart}
            onClick={startPrint}
            type="button"
            title={startBlockedReason || "Klaar om printstart te verzenden"}
          >
            {busy === "preflight" ? "Controleren..." : busy === "start" ? "Start verzenden..." : "Print starten"}
          </button>
        </div>
        <div
          className={`mt-3 rounded-lg border px-3 py-2 text-sm font-semibold ${
            startBlockedReason
              ? "border-amber-400/25 bg-amber-400/10 text-amber-100"
              : "border-emerald-400/25 bg-emerald-400/10 text-emerald-100"
          }`}
        >
          {startBlockedReason || "Klaar voor printstart. De controle draait automatisch zodra je op Print starten klikt."}
        </div>
        </div>
      </details>
    </div>
  );
}

function WorkflowStep({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="rounded-md border border-line bg-slate-950/35 p-3">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-black text-slate-950">{number}</span>
        <span className="font-bold text-ink">{title}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
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
