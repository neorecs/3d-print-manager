"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  platformId: number;
  platformType: string;
};

export function InventorySyncButton({ platformId, platformType }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function syncInventory() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/platforms/${platformId}/sync-inventory`, { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || data?.message || "Voorraad-sync is mislukt");
      const missing = data.missing_inventory_links?.length ? ` ${data.missing_inventory_links.length} variant(en) missen nog een Shopify inventory-link.` : "";
      setMessage(`${data.message || "Voorraad-sync klaar"} Voorbereid: ${data.prepared || 0}.${missing}`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Voorraad-sync is mislukt");
    } finally {
      setBusy(false);
    }
  }

  if (platformType.toLowerCase() !== "shopify") {
    return <p className="text-sm text-muted">Voorraad-sync is nu alleen beschikbaar voor Shopify.</p>;
  }

  return (
    <div className="space-y-3">
      <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busy} onClick={syncInventory} type="button">
        {busy ? "Voorraad synchroniseren..." : "Shopify voorraad synchroniseren"}
      </button>
      <p className="text-sm leading-6 text-muted">
        Synchroniseert vrije voorraad naar Shopify. Live-modus vereist `location_id` en opgeslagen Shopify inventory-item-ID's per variant.
      </p>
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}
    </div>
  );
}
