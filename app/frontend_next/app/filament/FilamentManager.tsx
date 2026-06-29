"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { formatCurrency } from "@/lib/api";
import type { FilamentSpool } from "@/lib/types";

type FilamentDraft = {
  brand: string;
  material: string;
  color: string;
  initial_weight_grams: string;
  remaining_weight_grams: string;
  purchase_price: string;
  minimum_remaining_grams: string;
  location: string;
  active: boolean;
};

function valueToString(value?: number | null) {
  return value === null || value === undefined ? "" : String(value);
}

function numberOrZero(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function emptyDraft(): FilamentDraft {
  return {
    brand: "",
    material: "PLA",
    color: "",
    initial_weight_grams: "1000",
    remaining_weight_grams: "1000",
    purchase_price: "",
    minimum_remaining_grams: "100",
    location: "",
    active: true,
  };
}

function draftFromSpool(spool: FilamentSpool): FilamentDraft {
  return {
    brand: spool.brand || "",
    material: spool.material || "",
    color: spool.color || "",
    initial_weight_grams: valueToString(spool.initial_weight_grams),
    remaining_weight_grams: valueToString(spool.remaining_weight_grams),
    purchase_price: valueToString(spool.purchase_price),
    minimum_remaining_grams: valueToString(spool.minimum_remaining_grams),
    location: spool.location || "",
    active: spool.active !== false,
  };
}

function toPayload(draft: FilamentDraft) {
  return {
    brand: draft.brand,
    material: draft.material,
    color: draft.color,
    initial_weight_grams: numberOrZero(draft.initial_weight_grams),
    remaining_weight_grams: numberOrZero(draft.remaining_weight_grams),
    purchase_price: numberOrZero(draft.purchase_price),
    minimum_remaining_grams: numberOrZero(draft.minimum_remaining_grams),
    location: draft.location || null,
    active: draft.active,
  };
}

export function FilamentManager({ filament }: { filament: FilamentSpool[] }) {
  const router = useRouter();
  const [newDraft, setNewDraft] = useState<FilamentDraft>(() => emptyDraft());
  const [drafts, setDrafts] = useState<Record<number, FilamentDraft>>(() =>
    Object.fromEntries(filament.map((spool) => [spool.id, draftFromSpool(spool)])),
  );
  const [adjustments, setAdjustments] = useState<Record<number, string>>(() =>
    Object.fromEntries(filament.map((spool) => [spool.id, valueToString(spool.remaining_weight_grams)])),
  );
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateNew(field: keyof FilamentDraft, value: string | boolean) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateDraft(id: number, field: keyof FilamentDraft, value: string | boolean) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  async function createSpool(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("new");
    setMessage(null);
    setError(null);

    try {
      const response = await fetch("/api/filament", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(newDraft)),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Filamentrol kon niet worden aangemaakt");
      }

      setNewDraft(emptyDraft());
      setMessage("Filamentrol aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Filament opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function saveSpool(id: number) {
    setBusyKey(`save-${id}`);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/filament/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(drafts[id])),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Filamentrol kon niet worden opgeslagen");
      }

      setMessage("Filamentrol opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Filament opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function adjustSpool(id: number) {
    setBusyKey(`adjust-${id}`);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/filament/${id}/adjust`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remaining_weight_grams: numberOrZero(adjustments[id] || "0") }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Resterend gewicht kon niet worden bijgewerkt");
      }

      setMessage("Resterend gewicht bijgewerkt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Gewicht aanpassen is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={createSpool}>
        <div className="mb-4">
          <h3 className="font-bold text-ink">Filamentrol toevoegen</h3>
          <p className="mt-1 text-sm text-muted">Leg merk, materiaal, kleur, gewicht en aankoopprijs vast. De prijs per gram wordt automatisch berekend.</p>
        </div>
        <FilamentFields draft={newDraft} onChange={updateNew} />
        <div className="mt-4 flex justify-end">
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busyKey === "new"}
            type="submit"
          >
            {busyKey === "new" ? "Aanmaken..." : "Filamentrol aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {filament.length ? (
          filament.map((spool) => {
            const draft = drafts[spool.id] || draftFromSpool(spool);
            const remaining = Number(spool.remaining_weight_grams || 0);
            const minimum = Number(spool.minimum_remaining_grams || 0);
            const lowStock = spool.active && remaining <= minimum;
            const used = Math.max(Number(spool.initial_weight_grams || 0) - remaining, 0);

            return (
              <details className="rounded-lg border border-line bg-panelSoft p-4 shadow-card" key={spool.id}>
                <summary className="cursor-pointer list-none">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="font-bold text-ink">{spool.brand} - {spool.material} - {spool.color}</div>
                      <p className="mt-1 text-sm text-muted">
                        {remaining}g resterend, {used}g gebruikt, {spool.location || "geen locatie"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${lowStock ? "bg-amber-400/10 text-amber-200" : "bg-emerald-400/10 text-emerald-300"}`}>
                        {lowStock ? "lage voorraad" : "voldoende"}
                      </span>
                      <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-bold text-slate-300">
                        {formatCurrency(spool.price_per_gram || 0)} / g
                      </span>
                    </div>
                  </div>
                </summary>
                <div className="mt-4 border-t border-line pt-4">
                  <FilamentFields draft={draft} onChange={(field, value) => updateDraft(spool.id, field, value)} />
                  <div className="mt-4 flex justify-end">
                    <button
                      className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={busyKey !== null}
                      onClick={() => saveSpool(spool.id)}
                      type="button"
                    >
                      {busyKey === `save-${spool.id}` ? "Opslaan..." : "Filamentrol opslaan"}
                    </button>
                  </div>

                  <div className="mt-5 rounded-lg border border-line bg-slate-950/25 p-4">
                    <h4 className="font-bold text-ink">Resterend gewicht snel bijwerken</h4>
                    <p className="mt-1 text-sm text-muted">Gebruik dit na een print of bij een weegcorrectie.</p>
                    <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
                      <TextField
                        inputMode="decimal"
                        label="Resterend gewicht gram"
                        onChange={(value) => setAdjustments((current) => ({ ...current, [spool.id]: value }))}
                        value={adjustments[spool.id] || ""}
                      />
                      <button
                        className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={busyKey !== null}
                        onClick={() => adjustSpool(spool.id)}
                        type="button"
                      >
                        {busyKey === `adjust-${spool.id}` ? "Bijwerken..." : "Gewicht bijwerken"}
                      </button>
                    </div>
                  </div>
                </div>
              </details>
            );
          })
        ) : (
          <div className="rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-200">
            Nog geen filamentrollen. Voeg hierboven je eerste rol toe.
          </div>
        )}
      </div>
    </div>
  );
}

function FilamentFields({
  draft,
  onChange,
}: {
  draft: FilamentDraft;
  onChange: (field: keyof FilamentDraft, value: string | boolean) => void;
}) {
  const pricePerGram = numberOrZero(draft.initial_weight_grams) > 0 ? numberOrZero(draft.purchase_price) / numberOrZero(draft.initial_weight_grams) : 0;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextField label="Merk" value={draft.brand} onChange={(value) => onChange("brand", value)} placeholder="Bijv. Bambu Lab" />
      <TextField label="Materiaal" value={draft.material} onChange={(value) => onChange("material", value)} placeholder="PLA, PETG, TPU" />
      <TextField label="Kleur" value={draft.color} onChange={(value) => onChange("color", value)} placeholder="Bijv. Rood" />
      <TextField label="Locatie" value={draft.location} onChange={(value) => onChange("location", value)} placeholder="Bijv. Rek A" />
      <TextField inputMode="decimal" label="Startgewicht gram" value={draft.initial_weight_grams} onChange={(value) => onChange("initial_weight_grams", value)} />
      <TextField inputMode="decimal" label="Resterend gram" value={draft.remaining_weight_grams} onChange={(value) => onChange("remaining_weight_grams", value)} />
      <TextField inputMode="decimal" label="Aankoopprijs" value={draft.purchase_price} onChange={(value) => onChange("purchase_price", value)} />
      <TextField inputMode="decimal" label="Minimum gram" value={draft.minimum_remaining_grams} onChange={(value) => onChange("minimum_remaining_grams", value)} />
      <div className="rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink">
        <div className="text-sm font-bold text-slate-300">Berekende prijs per gram</div>
        <div className="mt-1 text-lg font-bold text-ink">{formatCurrency(pricePerGram)}</div>
      </div>
      <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink font-semibold">
        <input checked={draft.active} onChange={(event) => onChange("active", event.target.checked)} type="checkbox" />
        Rol actief
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
