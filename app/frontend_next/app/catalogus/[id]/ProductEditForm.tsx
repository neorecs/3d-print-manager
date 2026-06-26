"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { Product } from "@/lib/types";

const statuses = [
  { value: "concept", label: "Concept" },
  { value: "klaar_voor_publicatie", label: "Klaar voor publicatie" },
  { value: "gepubliceerd", label: "Gepubliceerd" },
  { value: "gepauzeerd", label: "Gepauzeerd" },
  { value: "gearchiveerd", label: "Gearchiveerd" },
];

export function ProductEditForm({ product }: { product: Product }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState(product.name || "");
  const [title, setTitle] = useState(product.internal_title || "");
  const [category, setCategory] = useState(product.internal_category || "");
  const [productType, setProductType] = useState(product.product_type || "");
  const [status, setStatus] = useState(product.status || "concept");
  const [shortDescription, setShortDescription] = useState(product.short_description || "");
  const [longDescription, setLongDescription] = useState(product.long_description || "");
  const [salesDescription, setSalesDescription] = useState(product.sales_description || "");
  const [seoTitle, setSeoTitle] = useState(product.seo_title || "");
  const [seoDescription, setSeoDescription] = useState(product.seo_description || "");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch(`/api/products/${product.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          internal_title: title || name,
          short_description: shortDescription || null,
          long_description: longDescription || null,
          sales_description: salesDescription || null,
          seo_title: seoTitle || null,
          seo_description: seoDescription || null,
          product_type: productType || null,
          internal_category: category || null,
          status,
          active: product.active !== false,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Product kon niet worden opgeslagen");
      }

      setMessage("Productbasis opgeslagen. Platformpublicaties worden gemarkeerd als synchronisatie nodig.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <TextField label="Interne naam" value={name} onChange={setName} required />
        <TextField label="Producttitel" value={title} onChange={setTitle} />
        <TextField label="Categorie" value={category} onChange={setCategory} />
        <TextField label="Producttype" value={productType} onChange={setProductType} />
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-700">Status</span>
          <select
            className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {statuses.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <TextField label="SEO-titel" value={seoTitle} onChange={setSeoTitle} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TextArea label="Korte omschrijving" value={shortDescription} onChange={setShortDescription} />
        <TextArea label="Verkooptekst" value={salesDescription} onChange={setSalesDescription} />
        <TextArea label="Lange omschrijving" value={longDescription} onChange={setLongDescription} />
        <TextArea label="SEO-omschrijving" value={seoDescription} onChange={setSeoDescription} />
      </div>

      <div className="flex justify-end">
        <button
          className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={saving || !name}
          type="submit"
        >
          {saving ? "Opslaan..." : "Productbasis opslaan"}
        </button>
      </div>
    </form>
  );
}

function TextField({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        required={required}
        value={value}
      />
    </label>
  );
}

function TextArea({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <textarea
        className="min-h-28 w-full resize-y rounded-md border border-line bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}
