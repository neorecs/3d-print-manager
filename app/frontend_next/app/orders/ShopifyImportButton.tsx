"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function ShopifyImportButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [since, setSince] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function importOrders() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const query = since ? `?since=${encodeURIComponent(`${since}T00:00:00+00:00`)}` : "";
      const response = await fetch(`/api/orders/import/shopify${query}`, { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Shopify import is mislukt");
      const parts = [`${data.created || 0} nieuw`, `${data.updated || 0} bijgewerkt`, `${data.skipped || 0} overgeslagen`];
      const errorText = data.errors?.length ? ` Fouten: ${data.errors.map((item: { message: string }) => item.message).join("; ")}` : "";
      setMessage(`Shopify import klaar: ${parts.join(", ")}.${errorText}`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Shopify import is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy} onClick={importOrders} type="button">
        {busy ? "Shopify importeren..." : "Shopify orders importeren"}
      </button>
      <label className="block max-w-xs space-y-2">
        <span className="text-sm font-bold text-slate-700">Importeer vanaf</span>
        <input className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand" onChange={(event) => setSince(event.target.value)} type="date" value={since} />
      </label>
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}
    </div>
  );
}
