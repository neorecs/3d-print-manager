"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { SalesMarket } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

type MarketDraft = {
  country_code: string;
  country_name: string;
  primary_language: string;
  additional_languages: string;
  currency: string;
  active: boolean;
  note: string;
};

function emptyDraft(): MarketDraft {
  return {
    country_code: "",
    country_name: "",
    primary_language: "nl",
    additional_languages: "",
    currency: "EUR",
    active: true,
    note: "",
  };
}

function draftFromMarket(market: SalesMarket): MarketDraft {
  return {
    country_code: market.country_code || "",
    country_name: market.country_name || "",
    primary_language: market.primary_language || "nl",
    additional_languages: market.additional_languages || "",
    currency: market.currency || "EUR",
    active: market.active !== false,
    note: market.note || "",
  };
}

function toPayload(draft: MarketDraft) {
  return {
    country_code: draft.country_code.trim().toUpperCase(),
    country_name: draft.country_name.trim(),
    primary_language: draft.primary_language.trim().toLowerCase() || "nl",
    additional_languages: draft.additional_languages.trim() || null,
    currency: draft.currency.trim().toUpperCase() || "EUR",
    active: draft.active,
    note: draft.note.trim() || null,
  };
}

function languageSummary(market: SalesMarket) {
  const languages = [market.primary_language, ...(market.additional_languages || "").split(",")]
    .map((language) => language.trim())
    .filter(Boolean);
  return Array.from(new Set(languages)).join(", ");
}

export function SalesMarketsManager({ markets }: { markets: SalesMarket[] }) {
  const router = useRouter();
  const [newDraft, setNewDraft] = useState<MarketDraft>(() => emptyDraft());
  const [drafts, setDrafts] = useState<Record<number, MarketDraft>>(() => Object.fromEntries(markets.map((market) => [market.id, draftFromMarket(market)])));
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateNew(field: keyof MarketDraft, value: string | boolean) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateExisting(id: number, field: keyof MarketDraft, value: string | boolean) {
    setDrafts((current) => ({ ...current, [id]: { ...current[id], [field]: value } }));
  }

  async function createMarket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("new");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/sales-markets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(newDraft)),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Doelland kon niet worden aangemaakt");
      setNewDraft(emptyDraft());
      setMessage("Doelland aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function saveMarket(id: number) {
    setBusyKey(String(id));
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/sales-markets/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(drafts[id])),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Doelland kon niet worden opgeslagen");
      setMessage("Doelland opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <div className="grid gap-3 md:grid-cols-3">
        {markets.map((market) => (
          <article className="rounded-lg border border-line bg-panelSoft p-4" key={market.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-bold uppercase text-muted">{market.country_code}</div>
                <h3 className="mt-1 font-bold text-ink">{market.country_name}</h3>
              </div>
              <StatusBadge status={market.active ? "actief" : "inactief"} />
            </div>
            <div className="mt-3 text-sm leading-6 text-slate-300">
              Talen: <strong>{languageSummary(market)}</strong>
              <br />
              Valuta: <strong>{market.currency}</strong>
            </div>
            {market.note ? <p className="mt-2 text-sm leading-6 text-muted">{market.note}</p> : null}
          </article>
        ))}
      </div>

      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={createMarket}>
        <h3 className="font-bold text-ink">Doelland toevoegen</h3>
        <MarketFields draft={newDraft} onChange={updateNew} />
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === "new"} type="submit">
            {busyKey === "new" ? "Aanmaken..." : "Doelland aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {markets.map((market) => {
          const draft = drafts[market.id] || draftFromMarket(market);
          return (
            <details className="rounded-lg border border-line bg-panelSoft p-4" key={market.id}>
              <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-ink">{market.country_name}</div>
                    <div className="mt-1 text-sm text-muted">{market.country_code} - talen {languageSummary(market)}</div>
                  </div>
                  <StatusBadge status={market.active ? "actief" : "inactief"} />
                </div>
              </summary>
              <div className="mt-4 border-t border-line pt-4">
                <MarketFields draft={draft} onChange={(field, value) => updateExisting(market.id, field, value)} />
                <div className="mt-4 flex justify-end">
                  <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === String(market.id)} onClick={() => saveMarket(market.id)} type="button">
                    {busyKey === String(market.id) ? "Opslaan..." : "Doelland opslaan"}
                  </button>
                </div>
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}

function MarketFields({ draft, onChange }: { draft: MarketDraft; onChange: (field: keyof MarketDraft, value: string | boolean) => void }) {
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <TextField label="Landcode" value={draft.country_code} onChange={(value) => onChange("country_code", value)} placeholder="NL, BE, DE" />
      <TextField label="Landnaam" value={draft.country_name} onChange={(value) => onChange("country_name", value)} placeholder="Nederland" />
      <TextField label="Hoofdtaal" value={draft.primary_language} onChange={(value) => onChange("primary_language", value)} placeholder="nl, de, fr" />
      <TextField label="Extra talen" value={draft.additional_languages} onChange={(value) => onChange("additional_languages", value)} placeholder="Bijv. fr, en" />
      <TextField label="Valuta" value={draft.currency} onChange={(value) => onChange("currency", value)} placeholder="EUR" />
      <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm font-semibold">
        <input checked={draft.active} onChange={(event) => onChange("active", event.target.checked)} type="checkbox" />
        Actief verkoopland
      </label>
      <label className="space-y-2 md:col-span-2">
        <span className="text-sm font-bold text-slate-300">Notitie</span>
        <textarea className="min-h-20 w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand" onChange={(event) => onChange("note", event.target.value)} value={draft.note} />
      </label>
    </div>
  );
}

function TextField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} value={value} />
    </label>
  );
}

