"use client";

import { FormEvent, useState } from "react";
import type { AIProductStatus } from "@/lib/types";

type DraftInput = {
  idea: string;
  audience: string;
  style: string;
  material: string;
  colors: string;
  product_type: string;
  category: string;
  price: string;
  print_time: string;
  filament: string;
  dimensions: string;
  keywords: string;
  platforms: string;
};

function emptyInput(): DraftInput {
  return {
    idea: "",
    audience: "",
    style: "",
    material: "PLA",
    colors: "",
    product_type: "",
    category: "",
    price: "",
    print_time: "",
    filament: "",
    dimensions: "",
    keywords: "",
    platforms: "etsy, shopify",
  };
}

function mockDraft(input: DraftInput) {
  const title = input.idea.trim() || "Nieuw 3D print product";
  const colorList = input.colors.split(",").map((item) => item.trim()).filter(Boolean);
  const baseColor = colorList[0] || "kleur naar keuze";
  const tags = [input.product_type, input.category, input.material, baseColor, input.audience, input.keywords]
    .flatMap((item) => (item || "").split(","))
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 12);
  return {
    source: "gratis_mockmodus",
    product: {
      name: title,
      internal_title: title,
      short_description: `3D-geprint ${input.product_type || "product"} voor ${input.audience || "dagelijks gebruik"}.`,
      long_description: `Concept op basis van jouw idee: ${title}. Controleer maatvoering, materiaal en verkoopclaims voordat je publiceert.`,
      sales_description: `Voeg een persoonlijk en netjes afgewerkt 3D-print item toe aan je collectie. Materiaal: ${input.material || "n.t.b."}.`,
      seo_title: `${title} | 3D geprint`,
      seo_description: `Bekijk dit 3D-geprinte ${input.product_type || "product"} in ${baseColor}.`,
      product_type: input.product_type || "3D print product",
      internal_category: input.category || "Nog te categoriseren",
      status: "concept",
      active: true,
    },
    tags,
    variants: [
      {
        variant_name: `${baseColor} ${input.material || "materiaal"}`,
        sku: title.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").toUpperCase().slice(0, 36),
        color: baseColor,
        material: input.material || "PLA",
        estimated_print_time_minutes: input.print_time ? Number(input.print_time) : null,
        estimated_filament_grams: input.filament ? Number(input.filament) : null,
        default_sale_price: input.price ? Number(input.price.replace(",", ".")) : null,
        active: true,
      },
    ],
    checklist: ["Controleer printbestand", "Voeg echte foto's toe", "Controleer platformcategorie", "Controleer prijs en verzendprofiel"],
  };
}

export function AIProductAssistant({ status }: { status: AIProductStatus }) {
  const [input, setInput] = useState<DraftInput>(() => emptyInput());
  const [result, setResult] = useState<object | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof DraftInput, value: string) {
    setInput((current) => ({ ...current, [field]: value }));
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (!status.ready) {
        setResult(mockDraft(input));
        return;
      }
      const response = await fetch("/api/ai/product-draft/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...input,
          price: input.price ? Number(input.price.replace(",", ".")) : null,
          print_time: input.print_time ? Number(input.print_time) : null,
          filament: input.filament ? Number(input.filament.replace(",", ".")) : null,
          platforms: input.platforms.split(",").map((item) => item.trim()).filter(Boolean),
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "AI-generatie is mislukt");
      setResult(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "AI-generatie is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className={`rounded-md border px-4 py-3 text-sm ${status.ready ? "border-amber-200 bg-amber-50 text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>
        <strong>{status.ready ? "Echte AI staat klaar." : "Gratis mockmodus actief."}</strong> {status.ready ? status.note : "Er worden geen betaalde OpenAI-calls gedaan."}
      </div>
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-white p-4" onSubmit={generate}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 md:col-span-2">
            <span className="text-sm font-bold text-slate-700">Productidee</span>
            <textarea className="min-h-28 w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-brand" onChange={(event) => update("idea", event.target.value)} value={input.idea} />
          </label>
          <Field label="Doelgroep" value={input.audience} onChange={(value) => update("audience", value)} />
          <Field label="Stijl" value={input.style} onChange={(value) => update("style", value)} />
          <Field label="Materiaal" value={input.material} onChange={(value) => update("material", value)} />
          <Field label="Kleuren" value={input.colors} onChange={(value) => update("colors", value)} />
          <Field label="Producttype" value={input.product_type} onChange={(value) => update("product_type", value)} />
          <Field label="Categorie" value={input.category} onChange={(value) => update("category", value)} />
          <Field label="Prijs" value={input.price} onChange={(value) => update("price", value)} />
          <Field label="Printtijd minuten" value={input.print_time} onChange={(value) => update("print_time", value)} />
          <Field label="Filament gram" value={input.filament} onChange={(value) => update("filament", value)} />
          <Field label="Afmetingen" value={input.dimensions} onChange={(value) => update("dimensions", value)} />
          <Field label="Zoekwoorden" value={input.keywords} onChange={(value) => update("keywords", value)} />
          <Field label="Platformen" value={input.platforms} onChange={(value) => update("platforms", value)} />
        </div>
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy || !input.idea.trim()} type="submit">
            {busy ? "Genereren..." : status.ready ? "Concept met echte AI maken" : "Gratis concept maken"}
          </button>
        </div>
      </form>

      {result ? (
        <div className="rounded-lg border border-line bg-slate-950 p-4 text-sm text-slate-50">
          <div className="mb-2 font-bold">Concept JSON</div>
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
        </div>
      ) : null}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input className="w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-brand" onChange={(event) => onChange(event.target.value)} value={value} />
    </label>
  );
}
