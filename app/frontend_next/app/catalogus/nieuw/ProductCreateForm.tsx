"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type ProductResponse = {
  id?: number;
  detail?: string;
};

const statuses = [
  { value: "concept", label: "Concept" },
  { value: "klaar_voor_publicatie", label: "Klaar voor publicatie" },
  { value: "gepubliceerd", label: "Gepubliceerd" },
  { value: "gepauzeerd", label: "Gepauzeerd" },
  { value: "gearchiveerd", label: "Gearchiveerd" },
];

function makeSku(title: string, color: string, material: string) {
  const source = [title, color, material].filter(Boolean).join("-");
  return source
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40)
    .toUpperCase();
}

export function ProductCreateForm() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeVariant, setIncludeVariant] = useState(true);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [productType, setProductType] = useState("");
  const [status, setStatus] = useState("concept");
  const [shortDescription, setShortDescription] = useState("");
  const [salesDescription, setSalesDescription] = useState("");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [variantName, setVariantName] = useState("");
  const [sku, setSku] = useState("");
  const [color, setColor] = useState("");
  const [material, setMaterial] = useState("PLA");
  const [printMinutes, setPrintMinutes] = useState("");
  const [filamentGrams, setFilamentGrams] = useState("");
  const [salePrice, setSalePrice] = useState("");
  const [costPrice, setCostPrice] = useState("");

  const suggestedSku = useMemo(() => makeSku(title || name, color, material), [color, material, name, title]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const productResponse = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          internal_title: title || name,
          short_description: shortDescription || null,
          sales_description: salesDescription || null,
          seo_title: seoTitle || null,
          seo_description: seoDescription || null,
          internal_category: category || null,
          product_type: productType || null,
          status,
          active: true,
        }),
      });
      const product = (await productResponse.json()) as ProductResponse;

      if (!productResponse.ok || !product.id) {
        throw new Error(product.detail || "Product kon niet worden opgeslagen");
      }

      if (includeVariant) {
        const finalSku = sku || suggestedSku;
        const variantResponse = await fetch("/api/product-variants", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_id: product.id,
            variant_name: variantName || `${color || "Standaard"} ${material || ""}`.trim() || "Standaard",
            sku: finalSku || `PRODUCT-${product.id}`,
            color: color || null,
            material: material || null,
            estimated_print_time_minutes: printMinutes ? Number(printMinutes) : null,
            estimated_filament_grams: filamentGrams ? Number(filamentGrams) : null,
            default_sale_price: salePrice ? Number(salePrice) : null,
            cost_price: costPrice ? Number(costPrice) : null,
            active: true,
          }),
        });

        if (!variantResponse.ok) {
          const variantError = await variantResponse.json().catch(() => null);
          throw new Error(variantError?.detail || "Product is gemaakt, maar de variant kon niet worden opgeslagen");
        }
      }

      router.push("/catalogus");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {error}
        </div>
      ) : null}

      <FormBlock title="Productbasis" description="Dit is de interne hoofdbron. Etsy, Shopify en andere platformen volgen later.">
        <div className="grid gap-4 md:grid-cols-2">
          <TextField label="Interne naam" value={name} onChange={setName} required placeholder="Bijv. Dumpling rood" />
          <TextField label="Producttitel" value={title} onChange={setTitle} placeholder="Titel die je later kunt gebruiken voor verkoop" />
          <TextField label="Categorie" value={category} onChange={setCategory} placeholder="Bijv. Decoratie" />
          <TextField label="Producttype" value={productType} onChange={setProductType} placeholder="Bijv. Sleutelhanger, beeldje, houder" />
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
        </div>
      </FormBlock>

      <FormBlock title="Tekst en SEO" description="Vul eerst kort en bruikbaar in. Later kan de AI-assistent dit uitbreiden.">
        <div className="grid gap-4 lg:grid-cols-2">
          <TextArea label="Korte omschrijving" value={shortDescription} onChange={setShortDescription} placeholder="Een korte uitleg voor overzicht en publicatiecontrole." />
          <TextArea label="Verkooptekst" value={salesDescription} onChange={setSalesDescription} placeholder="Waarom zou iemand dit product willen kopen?" />
          <TextField label="SEO-titel" value={seoTitle} onChange={setSeoTitle} placeholder="Zoekvriendelijke titel" />
          <TextField label="SEO-omschrijving" value={seoDescription} onChange={setSeoDescription} placeholder="Korte zoekomschrijving" />
        </div>
      </FormBlock>

      <FormBlock title="Eerste variant" description="Maak meteen een eerste SKU met materiaal, kleur, printtijd en prijs.">
        <label className="flex items-center gap-3 rounded-md border border-line bg-slate-50 px-3 py-3 text-sm font-semibold">
          <input checked={includeVariant} onChange={(event) => setIncludeVariant(event.target.checked)} type="checkbox" />
          Eerste variant direct aanmaken
        </label>
        {includeVariant ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <TextField label="Variantnaam" value={variantName} onChange={setVariantName} placeholder="Bijv. Rood PLA" />
            <TextField label="SKU" value={sku} onChange={setSku} placeholder={suggestedSku || "Automatisch voorstel"} />
            <TextField label="Kleur" value={color} onChange={setColor} placeholder="Bijv. Rood" />
            <TextField label="Materiaal" value={material} onChange={setMaterial} placeholder="Bijv. PLA" />
            <TextField label="Printtijd in minuten" value={printMinutes} onChange={setPrintMinutes} inputMode="numeric" placeholder="Bijv. 90" />
            <TextField label="Filament in gram" value={filamentGrams} onChange={setFilamentGrams} inputMode="decimal" placeholder="Bijv. 42" />
            <TextField label="Verkoopprijs" value={salePrice} onChange={setSalePrice} inputMode="decimal" placeholder="Bijv. 14.95" />
            <TextField label="Kostprijs" value={costPrice} onChange={setCostPrice} inputMode="decimal" placeholder="Bijv. 2.80" />
          </div>
        ) : null}
      </FormBlock>

      <div className="flex flex-wrap justify-end gap-3">
        <a className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700" href="/catalogus">
          Annuleren
        </a>
        <button
          className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={saving || !name}
          type="submit"
        >
          {saving ? "Opslaan..." : "Product aanmaken"}
        </button>
      </div>
    </form>
  );
}

function FormBlock({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-white shadow-card">
      <div className="border-b border-line px-4 py-4">
        <h2 className="text-base font-bold text-ink">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  required,
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
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
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <textarea
        className="min-h-28 w-full resize-y rounded-md border border-line bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}
