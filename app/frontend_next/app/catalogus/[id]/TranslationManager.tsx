"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Product, ProductTranslation } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

type Props = {
  product: Product;
  translations: ProductTranslation[];
};

const LANGUAGES = [
  { code: "de", label: "Duits", note: "Duitsland" },
  { code: "fr", label: "Frans", note: "Belgie" },
  { code: "en", label: "Engels", note: "optioneel" },
];

export function TranslationManager({ product, translations }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(["de", "fr"]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggleLanguage(languageCode: string) {
    setSelectedLanguages((current) =>
      current.includes(languageCode) ? current.filter((item) => item !== languageCode) : [...current, languageCode],
    );
  }

  async function generateTranslations() {
    if (!selectedLanguages.length) {
      setError("Kies minimaal een taal.");
      return;
    }
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/products/${product.id}/translations/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language_codes: selectedLanguages, overwrite }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Vertaling genereren is mislukt");
      const generated = data.generated?.length || 0;
      const skipped = data.skipped?.length || 0;
      setMessage(`${generated} vertaling(en) gegenereerd, ${skipped} overgeslagen.`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vertaling genereren is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-line bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-bold text-ink">Vertaalde teksten maken</div>
            <p className="mt-1 text-sm leading-6 text-muted">
              Maakt titel, omschrijvingen, SEO en tags voor gekozen talen. Nederlands blijft de interne brontekst.
            </p>
          </div>
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy || !selectedLanguages.length} onClick={generateTranslations} type="button">
            {busy ? "Genereren..." : "Vertalingen genereren"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {LANGUAGES.map((language) => (
            <label
              className={`rounded-md border px-3 py-2 text-sm font-bold ${selectedLanguages.includes(language.code) ? "border-brand bg-red-50 text-brand" : "border-line bg-white text-slate-700"}`}
              key={language.code}
            >
              <input checked={selectedLanguages.includes(language.code)} className="mr-2" onChange={() => toggleLanguage(language.code)} type="checkbox" />
              {language.label} <span className="font-normal text-muted">({language.note})</span>
            </label>
          ))}
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <input checked={overwrite} onChange={(event) => setOverwrite(event.target.checked)} type="checkbox" />
          Bestaande vertalingen overschrijven
        </label>
      </div>

      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      {translations.length ? (
        <div className="space-y-3">
          {translations.map((translation) => (
            <article className="rounded-lg border border-line bg-white p-4" key={translation.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-bold uppercase text-muted">{translation.language_code}</div>
                  <h3 className="mt-1 font-bold text-ink">{translation.title || "Geen titel"}</h3>
                </div>
                <StatusBadge status={translation.source || "manual"} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{translation.short_description || translation.sales_description || "Geen tekst"}</p>
              <div className="mt-3 text-sm text-muted">Tags: {translation.tags || "-"}</div>
            </article>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">Nog geen vertalingen opgeslagen.</p>
      )}
    </div>
  );
}
