"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import type { BambuPrinter, Product, ProductVariant } from "@/lib/types";

type Props = {
  product: Product;
  variants: ProductVariant[];
  printers: BambuPrinter[];
  fixedVariantId?: number;
  printJobId?: number;
  compact?: boolean;
};

export function BambuStudioOpenAction({ product, variants, printers, fixedVariantId, printJobId, compact = false }: Props) {
  const router = useRouter();
  const activeVariants = variants.filter((variant) => variant.active !== false);
  const activePrinters = printers.filter((printer) => printer.active);
  const initialVariant = activeVariants.find((variant) => variant.id === fixedVariantId) || activeVariants[0];
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [variantId, setVariantId] = useState(initialVariant ? String(initialVariant.id) : "");
  const [printerId, setPrinterId] = useState(activePrinters[0] ? String(activePrinters[0].id) : "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function launch() {
    if (!variantId || !printerId || !product.print_file_path) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await Promise.allSettled(
        activePrinters.map((printer) => fetch(`/api/bambu/printers/${printer.id}/refresh-status`, { method: "POST" })),
      );
      const response = await fetch(`/api/products/${product.id}/print-file/open-in-bambu-studio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          variant_id: Number(variantId),
          printer_id: Number(printerId),
          print_job_id: printJobId,
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.launcher_url) {
        throw new Error(data?.detail || "Bambu Studio kon niet worden geopend.");
      }
      const slot = data.preparation?.recommended_slot;
      const warnings = Array.isArray(data.preparation?.warnings) ? data.preparation.warnings : [];
      const preparationText = slot
        ? `Advies: gebruik ${data.preparation.printer_name} met ${slot.label}. Koppel deze rol bij Print plate in Bambu Studio.`
        : `${data.preparation?.printer_name || "De printer"} is gekozen. Selecteer het filament handmatig in Bambu Studio.`;
      setMessage([preparationText, ...warnings].join(" "));
      router.refresh();
      window.location.href = data.launcher_url;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Bambu Studio kon niet worden geopend.");
    } finally {
      setBusy(false);
    }
  }

  if (!product.print_file_path) {
    return <span className="text-xs font-bold text-amber-200">Geen printbestand</span>;
  }

  return (
    <div className={`relative ${compact ? "w-full" : "min-w-[16rem]"}`}>
      <button
        className="w-full rounded-md bg-brand px-3 py-2 text-sm font-black text-slate-950 hover:bg-brand/90 disabled:opacity-50"
        disabled={!activeVariants.length || !activePrinters.length}
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        Open in Bambu Studio
      </button>
      {open ? (
        <div className="absolute right-0 top-full z-50 mt-2 w-[min(26rem,calc(100vw-3rem))] space-y-3 rounded-lg border border-line bg-slate-950 p-3 shadow-card">
          {fixedVariantId ? (
            <div className="text-xs font-bold text-slate-300">
              {initialVariant?.variant_name || initialVariant?.sku || `Variant ${fixedVariantId}`}
              {initialVariant?.material || initialVariant?.color ? ` - ${initialVariant.material || "-"} / ${initialVariant.color || "-"}` : ""}
            </div>
          ) : (
            <label className="block space-y-1">
              <span className="text-xs font-bold text-slate-300">Variant</span>
              <select className="w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-sm text-ink" onChange={(event) => setVariantId(event.target.value)} value={variantId}>
                {activeVariants.map((variant) => (
                  <option key={variant.id} value={variant.id}>{variant.variant_name || variant.sku || `Variant ${variant.id}`} - {variant.material || "-"} / {variant.color || "-"}</option>
                ))}
              </select>
            </label>
          )}
          <label className="block space-y-1">
            <span className="text-xs font-bold text-slate-300">Voorkeursprinter</span>
            <select className="w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-sm text-ink" onChange={(event) => setPrinterId(event.target.value)} value={printerId}>
              {activePrinters.map((printer) => <option key={printer.id} value={printer.id}>{printer.name} - {printer.model || "model onbekend"}</option>)}
            </select>
          </label>
          <p className="text-xs leading-5 text-muted">De app adviseert automatisch een compatibele printer en AMS-rol. Het originele bestand blijft ongewijzigd. Koppel de rol bij Print plate; wijzig niet het filamentprofiel van het model.</p>
          {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 p-2 text-xs text-emerald-200">{message}</div> : null}
          {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 p-2 text-xs text-red-200">{error}</div> : null}
          <div className="flex gap-2">
            <button className="flex-1 rounded-md bg-brand px-3 py-2 text-sm font-black text-slate-950 disabled:opacity-50" disabled={busy || !variantId || !printerId} onClick={launch} type="button">
              {busy ? "Controleren..." : "Nu openen"}
            </button>
            <button className="rounded-md border border-line px-3 py-2 text-sm font-bold text-slate-300" onClick={() => setOpen(false)} type="button">Sluiten</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
