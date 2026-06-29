"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Product, ProductInventory, ProductVariant } from "@/lib/types";

type InventoryDraft = {
  product_variant_id: string;
  color: string;
  material: string;
  quantity_on_hand: string;
  quantity_reserved: string;
  minimum_stock_level: string;
  location: string;
};

function valueToString(value?: number | null) {
  return value === null || value === undefined ? "" : String(value);
}

function variantLabel(variant?: ProductVariant) {
  if (!variant) {
    return "Onbekende variant";
  }

  return [
    variant.variant_name || `Variant ${variant.id}`,
    variant.sku,
    variant.material,
    variant.color,
  ]
    .filter(Boolean)
    .join(" - ");
}

function emptyDraft(variants: ProductVariant[]): InventoryDraft {
  const firstVariant = variants[0];
  return {
    product_variant_id: firstVariant ? String(firstVariant.id) : "",
    color: firstVariant?.color || "",
    material: firstVariant?.material || "",
    quantity_on_hand: "0",
    quantity_reserved: "0",
    minimum_stock_level: "0",
    location: "",
  };
}

function draftFromInventory(item: ProductInventory): InventoryDraft {
  return {
    product_variant_id: String(item.product_variant_id),
    color: item.color || "",
    material: item.material || "",
    quantity_on_hand: valueToString(item.quantity_on_hand),
    quantity_reserved: valueToString(item.quantity_reserved),
    minimum_stock_level: valueToString(item.minimum_stock_level),
    location: item.location || "",
  };
}

function numberOrZero(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function toPayload(productId: number, draft: InventoryDraft) {
  return {
    product_id: productId,
    product_variant_id: Number(draft.product_variant_id),
    color: draft.color || null,
    material: draft.material || null,
    quantity_on_hand: numberOrZero(draft.quantity_on_hand),
    quantity_reserved: numberOrZero(draft.quantity_reserved),
    minimum_stock_level: numberOrZero(draft.minimum_stock_level),
    location: draft.location || null,
  };
}

export function InventoryManager({
  product,
  variants,
  inventory,
}: {
  product: Product;
  variants: ProductVariant[];
  inventory: ProductInventory[];
}) {
  const router = useRouter();
  const variantById = useMemo(() => new Map(variants.map((variant) => [variant.id, variant])), [variants]);
  const [newDraft, setNewDraft] = useState<InventoryDraft>(() => emptyDraft(variants));
  const [drafts, setDrafts] = useState<Record<number, InventoryDraft>>(() =>
    Object.fromEntries(inventory.map((item) => [item.id, draftFromInventory(item)])),
  );
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function syncVariantFields(draft: InventoryDraft, variantId: string) {
    const variant = variantById.get(Number(variantId));
    return {
      ...draft,
      product_variant_id: variantId,
      color: variant?.color || draft.color,
      material: variant?.material || draft.material,
    };
  }

  function updateNew(field: keyof InventoryDraft, value: string) {
    setNewDraft((current) => (field === "product_variant_id" ? syncVariantFields(current, value) : { ...current, [field]: value }));
  }

  function updateExisting(id: number, field: keyof InventoryDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: field === "product_variant_id" ? syncVariantFields(current[id], value) : { ...current[id], [field]: value },
    }));
  }

  async function createInventory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingKey("new");
    setMessage(null);
    setError(null);

    try {
      const response = await fetch("/api/inventory/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(product.id, newDraft)),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Voorraadregel kon niet worden aangemaakt");
      }

      setNewDraft(emptyDraft(variants));
      setMessage("Voorraadregel aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Voorraad opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  async function saveInventory(id: number) {
    setSavingKey(String(id));
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/inventory/products/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(product.id, drafts[id])),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Voorraadregel kon niet worden opgeslagen");
      }

      setMessage("Voorraadregel opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Voorraad opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={createInventory}>
        <div className="mb-4">
          <h3 className="font-bold text-ink">Voorraadregel toevoegen</h3>
          <p className="mt-1 text-sm text-muted">Maak per productvariant een voorraadregel met vrije voorraad, reserveringen, minimum en opslaglocatie.</p>
        </div>
        {variants.length ? (
          <>
            <InventoryFields draft={newDraft} variants={variants} onChange={updateNew} />
            <div className="mt-4 flex justify-end">
              <button
                className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={savingKey === "new" || !newDraft.product_variant_id}
                type="submit"
              >
                {savingKey === "new" ? "Aanmaken..." : "Voorraadregel aanmaken"}
              </button>
            </div>
          </>
        ) : (
          <div className="rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-800">
            Maak eerst minimaal een variant aan. Voorraad wordt altijd aan een variant gekoppeld.
          </div>
        )}
      </form>

      <div className="space-y-3">
        {inventory.length ? (
          inventory.map((item) => {
            const draft = drafts[item.id] || draftFromInventory(item);
            const freeStock = Math.max(Number(draft.quantity_on_hand || 0) - Number(draft.quantity_reserved || 0), 0);
            const minimum = Number(draft.minimum_stock_level || 0);
            const lowStock = freeStock <= minimum;

            return (
              <details className="rounded-lg border border-line bg-panelSoft p-4" key={item.id}>
                <summary className="cursor-pointer list-none">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-bold text-ink">{variantLabel(variantById.get(item.product_variant_id))}</div>
                      <div className="mt-1 text-sm text-muted">
                        {item.material || "-"} - {item.color || "-"} - {item.location || "geen locatie"}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-bold text-slate-300">
                        vrij: {Math.max(item.quantity_on_hand - item.quantity_reserved, 0)}
                      </span>
                      {lowStock ? (
                        <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800">lage voorraad</span>
                      ) : (
                        <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-300">voldoende</span>
                      )}
                    </div>
                  </div>
                </summary>
                <div className="mt-4 border-t border-line pt-4">
                  <InventoryFields
                    draft={draft}
                    variants={variants}
                    onChange={(field, value) => updateExisting(item.id, field, value)}
                  />
                  <div className="mt-4 rounded-md bg-panelSoft px-3 py-2 text-sm text-muted">
                    Vrije voorraad: <strong className="text-ink">{freeStock}</strong>. Minimum: <strong className="text-ink">{minimum}</strong>.
                  </div>
                  <div className="mt-4 flex justify-end">
                    <button
                      className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={savingKey === String(item.id)}
                      onClick={() => saveInventory(item.id)}
                      type="button"
                    >
                      {savingKey === String(item.id) ? "Opslaan..." : "Voorraad opslaan"}
                    </button>
                  </div>
                </div>
              </details>
            );
          })
        ) : (
          <div className="rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-800">
            Nog geen productvoorraad. Voeg hierboven de eerste voorraadregel toe.
          </div>
        )}
      </div>
    </div>
  );
}

function InventoryFields({
  draft,
  variants,
  onChange,
}: {
  draft: InventoryDraft;
  variants: ProductVariant[];
  onChange: (field: keyof InventoryDraft, value: string) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="space-y-2 md:col-span-2">
        <span className="text-sm font-bold text-slate-300">Variant</span>
        <select
          className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
          onChange={(event) => onChange("product_variant_id", event.target.value)}
          value={draft.product_variant_id}
        >
          {variants.map((variant) => (
            <option key={variant.id} value={variant.id}>
              {variantLabel(variant)}
            </option>
          ))}
        </select>
      </label>
      <TextField label="Kleur" value={draft.color} onChange={(value) => onChange("color", value)} />
      <TextField label="Materiaal" value={draft.material} onChange={(value) => onChange("material", value)} />
      <TextField label="Op voorraad" value={draft.quantity_on_hand} onChange={(value) => onChange("quantity_on_hand", value)} inputMode="numeric" />
      <TextField label="Gereserveerd" value={draft.quantity_reserved} onChange={(value) => onChange("quantity_reserved", value)} inputMode="numeric" />
      <TextField label="Minimumvoorraad" value={draft.minimum_stock_level} onChange={(value) => onChange("minimum_stock_level", value)} inputMode="numeric" />
      <TextField label="Locatie" value={draft.location} onChange={(value) => onChange("location", value)} placeholder="Bijv. Bak A1" />
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "decimal";
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}
