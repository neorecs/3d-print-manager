"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Product, ProductVariant } from "@/lib/types";

type VariantDraft = {
  variant_name: string;
  sku: string;
  color: string;
  material: string;
  size: string;
  finish: string;
  print_file_path: string;
  estimated_print_time_minutes: string;
  estimated_filament_grams: string;
  weight_grams: string;
  length_mm: string;
  width_mm: string;
  height_mm: string;
  default_sale_price: string;
  action_sale_price: string;
  cost_price: string;
  active: boolean;
};

function makeSku(title: string, color: string, material: string, suffix = "") {
  const source = [title, color, material, suffix].filter(Boolean).join("-");
  return source
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48)
    .toUpperCase();
}

function emptyDraft(product: Product): VariantDraft {
  return {
    variant_name: "",
    sku: "",
    color: "",
    material: "PLA",
    size: "",
    finish: "",
    print_file_path: "",
    estimated_print_time_minutes: "",
    estimated_filament_grams: "",
    weight_grams: "",
    length_mm: "",
    width_mm: "",
    height_mm: "",
    default_sale_price: "",
    action_sale_price: "",
    cost_price: "",
    active: product.active !== false,
  };
}

function draftFromVariant(variant: ProductVariant): VariantDraft {
  return {
    variant_name: variant.variant_name || "",
    sku: variant.sku || "",
    color: variant.color || "",
    material: variant.material || "",
    size: variant.size || "",
    finish: variant.finish || "",
    print_file_path: variant.print_file_path || "",
    estimated_print_time_minutes: valueToString(variant.estimated_print_time_minutes),
    estimated_filament_grams: valueToString(variant.estimated_filament_grams),
    weight_grams: valueToString(variant.weight_grams),
    length_mm: valueToString(variant.length_mm),
    width_mm: valueToString(variant.width_mm),
    height_mm: valueToString(variant.height_mm),
    default_sale_price: valueToString(variant.default_sale_price),
    action_sale_price: valueToString(variant.action_sale_price),
    cost_price: valueToString(variant.cost_price),
    active: variant.active !== false,
  };
}

function valueToString(value?: number | null) {
  return value === null || value === undefined ? "" : String(value);
}

function numberOrNull(value: string) {
  return value.trim() ? Number(value.replace(",", ".")) : null;
}

function toPayload(productId: number, draft: VariantDraft) {
  return {
    product_id: productId,
    variant_name: draft.variant_name || "Standaard",
    sku: draft.sku,
    color: draft.color || null,
    material: draft.material || null,
    size: draft.size || null,
    finish: draft.finish || null,
    print_file_path: draft.print_file_path || null,
    estimated_print_time_minutes: numberOrNull(draft.estimated_print_time_minutes),
    estimated_filament_grams: numberOrNull(draft.estimated_filament_grams),
    weight_grams: numberOrNull(draft.weight_grams),
    length_mm: numberOrNull(draft.length_mm),
    width_mm: numberOrNull(draft.width_mm),
    height_mm: numberOrNull(draft.height_mm),
    default_sale_price: numberOrNull(draft.default_sale_price),
    action_sale_price: numberOrNull(draft.action_sale_price),
    cost_price: numberOrNull(draft.cost_price),
    active: draft.active,
  };
}

export function VariantManager({ product, variants }: { product: Product; variants: ProductVariant[] }) {
  const router = useRouter();
  const [newDraft, setNewDraft] = useState<VariantDraft>(() => emptyDraft(product));
  const [editing, setEditing] = useState<Record<number, VariantDraft>>(() =>
    Object.fromEntries(variants.map((variant) => [variant.id, draftFromVariant(variant)])),
  );
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const suggestedSku = useMemo(
    () => makeSku(product.internal_title || product.name, newDraft.color, newDraft.material, String(variants.length + 1)),
    [newDraft.color, newDraft.material, product.internal_title, product.name, variants.length],
  );

  function updateNew(field: keyof VariantDraft, value: string | boolean) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateExisting(id: number, field: keyof VariantDraft, value: string | boolean) {
    setEditing((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  async function createVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingKey("new");
    setMessage(null);
    setError(null);

    try {
      const draft = { ...newDraft, sku: newDraft.sku || suggestedSku };
      const response = await fetch("/api/product-variants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(product.id, draft)),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Variant kon niet worden aangemaakt");
      }

      setNewDraft(emptyDraft(product));
      setMessage("Variant aangemaakt. Gekoppelde platformpublicaties krijgen synchronisatie nodig.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Variant opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  async function updateVariant(id: number) {
    setSavingKey(String(id));
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/product-variants/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(product.id, editing[id])),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Variant kon niet worden opgeslagen");
      }

      setMessage("Variant opgeslagen. Gekoppelde platformpublicaties krijgen synchronisatie nodig.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Variant opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-50 p-4" onSubmit={createVariant}>
        <div className="mb-4">
          <h3 className="font-bold text-ink">Nieuwe variant toevoegen</h3>
          <p className="mt-1 text-sm text-muted">Maak per kleur, materiaal of uitvoering een eigen SKU aan.</p>
        </div>
        <VariantFields
          draft={newDraft}
          fallbackSku={suggestedSku}
          onChange={updateNew}
        />
        <div className="mt-4 flex justify-end">
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={savingKey === "new"}
            type="submit"
          >
            {savingKey === "new" ? "Aanmaken..." : "Variant aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {variants.length ? (
          variants.map((variant) => {
            const draft = editing[variant.id] || draftFromVariant(variant);
            return (
              <details className="rounded-lg border border-line bg-white p-4" key={variant.id}>
                <summary className="cursor-pointer list-none">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-bold text-ink">{variant.variant_name || `Variant ${variant.id}`}</div>
                      <div className="mt-1 text-sm text-muted">{variant.sku || "Geen SKU"} · {variant.material || "-"} · {variant.color || "-"}</div>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                      {variant.active === false ? "inactief" : "actief"}
                    </span>
                  </div>
                </summary>
                <div className="mt-4 border-t border-line pt-4">
                  <VariantFields
                    draft={draft}
                    fallbackSku={makeSku(product.internal_title || product.name, draft.color, draft.material, String(variant.id))}
                    onChange={(field, value) => updateExisting(variant.id, field, value)}
                  />
                  <div className="mt-4 flex justify-end">
                    <button
                      className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={savingKey === String(variant.id)}
                      onClick={() => updateVariant(variant.id)}
                      type="button"
                    >
                      {savingKey === String(variant.id) ? "Opslaan..." : "Variant opslaan"}
                    </button>
                  </div>
                </div>
              </details>
            );
          })
        ) : (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            Nog geen varianten. Maak hierboven de eerste SKU aan.
          </div>
        )}
      </div>
    </div>
  );
}

function VariantFields({
  draft,
  fallbackSku,
  onChange,
}: {
  draft: VariantDraft;
  fallbackSku: string;
  onChange: (field: keyof VariantDraft, value: string | boolean) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextField label="Variantnaam" value={draft.variant_name} onChange={(value) => onChange("variant_name", value)} placeholder="Bijv. Rood PLA" />
      <TextField label="SKU" value={draft.sku} onChange={(value) => onChange("sku", value)} placeholder={fallbackSku || "Automatisch voorstel"} />
      <TextField label="Kleur" value={draft.color} onChange={(value) => onChange("color", value)} placeholder="Bijv. Rood" />
      <TextField label="Materiaal" value={draft.material} onChange={(value) => onChange("material", value)} placeholder="Bijv. PLA" />
      <TextField label="Maat" value={draft.size} onChange={(value) => onChange("size", value)} placeholder="Bijv. M, 10 cm, standaard" />
      <TextField label="Afwerking" value={draft.finish} onChange={(value) => onChange("finish", value)} placeholder="Bijv. mat, glans, silk" />
      <TextField label="Printbestand" value={draft.print_file_path} onChange={(value) => onChange("print_file_path", value)} placeholder="/PrintFiles/product.3mf" />
      <TextField label="Printtijd minuten" value={draft.estimated_print_time_minutes} onChange={(value) => onChange("estimated_print_time_minutes", value)} inputMode="numeric" />
      <TextField label="Filament gram" value={draft.estimated_filament_grams} onChange={(value) => onChange("estimated_filament_grams", value)} inputMode="decimal" />
      <TextField label="Gewicht gram" value={draft.weight_grams} onChange={(value) => onChange("weight_grams", value)} inputMode="decimal" />
      <TextField label="Lengte mm" value={draft.length_mm} onChange={(value) => onChange("length_mm", value)} inputMode="decimal" />
      <TextField label="Breedte mm" value={draft.width_mm} onChange={(value) => onChange("width_mm", value)} inputMode="decimal" />
      <TextField label="Hoogte mm" value={draft.height_mm} onChange={(value) => onChange("height_mm", value)} inputMode="decimal" />
      <TextField label="Verkoopprijs" value={draft.default_sale_price} onChange={(value) => onChange("default_sale_price", value)} inputMode="decimal" />
      <TextField label="Actieprijs" value={draft.action_sale_price} onChange={(value) => onChange("action_sale_price", value)} inputMode="decimal" />
      <TextField label="Kostprijs" value={draft.cost_price} onChange={(value) => onChange("cost_price", value)} inputMode="decimal" />
      <label className="flex items-center gap-3 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold">
        <input checked={draft.active} onChange={(event) => onChange("active", event.target.checked)} type="checkbox" />
        Variant actief
      </label>
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
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}
