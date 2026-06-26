"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
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
  const platforms = input.platforms.split(",").map((item) => item.trim().toLowerCase()).filter(Boolean);
  const platformPublications = Object.fromEntries(
    platforms.map((platform) => [
      platform,
      {
        platform_title: title,
        platform_description: `Concept voor ${platform}: ${title}. Controleer platformcategorie, tags, prijs en foto's voordat je publiceert.`,
        platform_category: input.category || "Nog te kiezen",
        platform_tags: tags.join(", "),
        platform_price_override: input.price ? Number(input.price.replace(",", ".")) : null,
        publication_status: "concept",
      },
    ]),
  );

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
    platform_publications: platformPublications,
    checklist: ["Controleer printbestand", "Voeg echte foto's toe", "Controleer platformcategorie", "Controleer prijs en verzendprofiel"],
  };
}

export function AIProductAssistant({ status }: { status: AIProductStatus }) {
  const router = useRouter();
  const [input, setInput] = useState<DraftInput>(() => emptyInput());
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [saveResult, setSaveResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof DraftInput, value: string) {
    setInput((current) => ({ ...current, [field]: value }));
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaveResult(null);
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

  async function saveConcept() {
    if (!result) {
      return;
    }

    setSaving(true);
    setError(null);
    setSaveResult(null);
    try {
      const response = await fetch("/api/ai/product-draft/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.detail || "Concept opslaan is mislukt");
      }
      setSaveResult(data);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Concept opslaan is mislukt");
    } finally {
      setSaving(false);
    }
  }

  const savedProductId = typeof saveResult?.product_id === "number" ? saveResult.product_id : null;
  const warnings = Array.isArray(saveResult?.warnings) ? saveResult.warnings.map((item) => String(item)) : [];

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
        <div className="space-y-4">
          <div className="rounded-lg border border-line bg-white p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 className="font-bold text-ink">Concept klaar om op te slaan</h3>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Opslaan maakt een intern conceptproduct met tags, varianten en concept-platformpublicaties. Er wordt niets gepubliceerd.
                </p>
              </div>
              <button
                className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={saving}
                onClick={saveConcept}
                type="button"
              >
                {saving ? "Opslaan..." : "Concept opslaan als product"}
              </button>
            </div>
            {saveResult ? (
              <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800">
                <div className="font-bold">Concept opgeslagen{savedProductId ? ` als product #${savedProductId}` : ""}.</div>
                {savedProductId ? (
                  <a className="mt-2 inline-block rounded-md border border-emerald-300 bg-white px-3 py-2 text-sm font-bold text-emerald-800" href={`/catalogus/${savedProductId}`}>
                    Product openen
                  </a>
                ) : null}
                {warnings.length ? (
                  <ul className="mt-3 list-disc space-y-1 pl-5">
                    {warnings.map((warning) => <li key={warning}>{warning}</li>)}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="rounded-lg border border-line bg-slate-950 p-4 text-sm text-slate-50">
            <div className="mb-2 font-bold">Concept JSON</div>
            <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
          </div>
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
