type Handoff = {
  launcher_url: string;
  warnings?: string[];
  preparation?: {
    printer_name?: string;
    last_seen_at?: string | null;
    recommended_slot?: { label?: string } | null;
    warnings?: string[];
  } | null;
};

export function studioHandoffMessage(data: Handoff): string {
  const preparation = data.preparation;
  const advice = preparation
    ? `Printeradvies: ${preparation.printer_name || "kies een printer"}${preparation.recommended_slot?.label ? `, ${preparation.recommended_slot.label}` : ""}. Controleer printer en filament in Bambu Studio.`
    : "Kies printer, filament en slice-instellingen in Bambu Studio.";
  const seen = preparation?.last_seen_at ? new Date(preparation.last_seen_at) : null;
  const observation = preparation
    ? seen && Number.isFinite(seen.getTime()) ? `Laatste printermeting: ${seen.toLocaleString("nl-NL")}.` : "Tijdstip printermeting onbekend."
    : "";
  return ["Bestand aangeboden aan Bambu Studio.", advice, observation, ...(preparation?.warnings || []), ...(data.warnings || [])].filter(Boolean).join(" ");
}

export function readablePrintFilename(path: string): string {
  return (path.split(/[\\/]/).pop() || path).replace(/^[a-f0-9]{32}-/i, "");
}

export function amsRemainingLabel(percent: number | null | undefined): string {
  return typeof percent === "number" && Number.isFinite(percent) && percent >= 0 && percent <= 100
    ? `${Math.round(percent)}%`
    : "restvoorraad onbekend";
}

export async function requestStudioHandoff(productId: number, variantId?: number, printerId?: number, printJobId?: number) {
  const response = await fetch(`/api/products/${productId}/print-file/open-in-bambu-studio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variant_id: variantId || null, printer_id: printerId || null, print_job_id: printJobId }),
    signal: AbortSignal.timeout(20000),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.launcher_url) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "Bambu Studio kon niet worden geopend. Probeer opnieuw of download het bestand.");
  }
  return data as Handoff;
}
