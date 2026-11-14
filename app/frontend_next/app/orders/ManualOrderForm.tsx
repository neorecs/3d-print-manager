"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAssistedType } from "@/lib/channels";
import type { Platform } from "@/lib/types";

type Variant = { id: number; sku: string; variant_name: string; default_sale_price?: number | null; active?: boolean };

/** Record an order from a channel without order import (Marktplaats, Vinted, ...). */
export function ManualOrderForm({ platforms }: { platforms: Platform[] }) {
  const router = useRouter();
  const channels = platforms.filter((platform) => platform.active && isAssistedType(platform.type));
  const [variants, setVariants] = useState<Variant[]>([]);
  const [platformId, setPlatformId] = useState<string>(channels[0] ? String(channels[0].id) : "");
  const [variantId, setVariantId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState("");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/product-variants")
      .then((response) => (response.ok ? response.json() : []))
      .then((rows: Variant[]) => setVariants(rows.filter((row) => row.active !== false)))
      .catch(() => setVariants([]));
  }, []);

  if (!channels.length) {
    return <p className="text-sm text-muted">Voeg eerst een verkoopkanaal in hulpmodus toe (bijvoorbeeld Marktplaats of Vinted) onder Verkoopkanalen.</p>;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch("/api/orders/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform_id: Number(platformId),
          external_order_id: reference.trim() || null,
          items: [{ product_variant_id: Number(variantId), quantity: Number(quantity), unit_price: price ? Number(price.replace(",", ".")) : null }],
          process: true,
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "Order opslaan is mislukt.");
      setMessage(`Order ${data.order?.internal_order_number ?? ""} opgeslagen. ${data.message ?? ""}`.trim());
      setReference("");
      router.refresh();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Order opslaan is mislukt.");
    } finally {
      setBusy(false);
    }
  }

  const field = "min-h-10 rounded-lg border border-line bg-panel px-3 text-sm font-normal text-ink outline-none focus:border-brand";
  return (
    <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-5 xl:items-end" onSubmit={submit}>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Kanaal
        <select className={field} onChange={(event) => setPlatformId(event.target.value)} required value={platformId}>
          {channels.map((platform) => <option key={platform.id} value={platform.id}>{platform.name}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Product
        <select className={field} onChange={(event) => setVariantId(event.target.value)} required value={variantId}>
          <option value="">Kies een variant</option>
          {variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.variant_name} ({variant.sku})</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Aantal
        <input className={field} min={1} onChange={(event) => setQuantity(event.target.value)} required type="number" value={quantity} />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Prijs per stuk (€, optioneel)
        <input className={field} inputMode="decimal" onChange={(event) => setPrice(event.target.value)} placeholder="Standaardprijs" value={price} />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Kenmerk op het kanaal (optioneel)
        <input className={field} onChange={(event) => setReference(event.target.value)} placeholder="Bijv. advertentienummer" value={reference} />
      </label>
      <div className="flex flex-wrap items-center gap-3 md:col-span-2 xl:col-span-5">
        <button className="min-h-10 rounded-lg border border-brand bg-brand px-4 text-sm font-semibold text-onBrand disabled:opacity-60" disabled={busy || !variantId} type="submit">
          {busy ? "Opslaan..." : "Order opslaan en verwerken"}
        </button>
        {message ? <span className="text-sm text-muted">{message}</span> : null}
      </div>
    </form>
  );
}
