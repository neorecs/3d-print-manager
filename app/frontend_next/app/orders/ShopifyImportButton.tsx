"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function ShopifyImportButton() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [since, setSince] = useState("");
  const [limit, setLimit] = useState("100");
  const [pageSize, setPageSize] = useState("50");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function importOrders(platform: "shopify" | "etsy") {
    setBusy(platform);
    setMessage(null);
    setError(null);
    try {
      const params = new URLSearchParams({ limit, page_size: pageSize });
      if (since) params.set("since", `${since}T00:00:00+00:00`);
      const query = `?${params.toString()}`;
      const response = await fetch(`/api/orders/import/${platform}${query}`, { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || `${platform} import is mislukt`);
      const parts = [`${data.created || 0} nieuw`, `${data.updated || 0} bijgewerkt`, `${data.skipped || 0} overgeslagen`];
      const errorText = data.errors?.length ? ` Fouten: ${data.errors.map((item: { message: string }) => item.message).join("; ")}` : "";
      setMessage(`${platform === "shopify" ? "Shopify" : "Etsy"} import klaar: ${parts.join(", ")}.${errorText}`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Orderimport is mislukt");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-[minmax(180px,260px)_160px_160px_auto] md:items-end">
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-300">Importeer vanaf</span>
          <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => setSince(event.target.value)} type="date" value={since} />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-300">Max orders</span>
          <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" max="250" min="1" onChange={(event) => setLimit(event.target.value)} type="number" value={limit} />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-300">Paginaformaat</span>
          <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" max="50" min="1" onChange={(event) => setPageSize(event.target.value)} type="number" value={pageSize} />
        </label>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={Boolean(busy)} onClick={() => importOrders("shopify")} type="button">
            {busy === "shopify" ? "Shopify importeren..." : "Shopify orders importeren"}
          </button>
          <button className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-60" disabled={Boolean(busy)} onClick={() => importOrders("etsy")} type="button">
            {busy === "etsy" ? "Etsy importeren..." : "Etsy orders importeren"}
          </button>
        </div>
      </div>
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}
    </div>
  );
}
