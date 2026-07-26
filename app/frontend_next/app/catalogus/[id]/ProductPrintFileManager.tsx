"use client";

import { ChangeEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { Product } from "@/lib/types";

export function ProductPrintFileManager({ product }: { product: Product }) {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printbestand uploaden is mislukt");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  const filename = product.print_file_path?.split("/").pop() || null;

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
    </div>
  );
}
