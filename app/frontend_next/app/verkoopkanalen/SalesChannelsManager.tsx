"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { Platform } from "@/lib/types";

type PlatformDraft = {
  name: string;
  type: string;
  api_base_url: string;
  active: boolean;
};

function emptyDraft(): PlatformDraft {
  return { name: "", type: "shopify", api_base_url: "", active: true };
}

function draftFromPlatform(platform: Platform): PlatformDraft {
  return {
    name: platform.name || "",
    type: platform.type || "",
    api_base_url: platform.api_base_url || "",
    active: platform.active !== false,
  };
}

function toPayload(draft: PlatformDraft) {
  return {
    name: draft.name,
    type: draft.type,
    api_base_url: draft.api_base_url || null,
    active: draft.active,
  };
}

export function SalesChannelsManager({ platforms }: { platforms: Platform[] }) {
  const router = useRouter();
  const [newDraft, setNewDraft] = useState<PlatformDraft>(() => emptyDraft());
  const [drafts, setDrafts] = useState<Record<number, PlatformDraft>>(() => Object.fromEntries(platforms.map((platform) => [platform.id, draftFromPlatform(platform)])));
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateNew(field: keyof PlatformDraft, value: string | boolean) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateExisting(id: number, field: keyof PlatformDraft, value: string | boolean) {
    setDrafts((current) => ({ ...current, [id]: { ...current[id], [field]: value } }));
  }

  async function createPlatform(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("new");
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/platforms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(newDraft)),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Verkoopkanaal kon niet worden aangemaakt");
      setNewDraft(emptyDraft());
      setMessage("Verkoopkanaal aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function savePlatform(id: number) {
    setBusyKey(String(id));
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/platforms/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(drafts[id])),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Verkoopkanaal kon niet worden opgeslagen");
      setMessage("Verkoopkanaal opgeslagen.");
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
      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={createPlatform}>
        <h3 className="font-bold text-ink">Verkoopkanaal toevoegen</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <TextField label="Naam" value={newDraft.name} onChange={(value) => updateNew("name", value)} placeholder="Bijv. Mijn Shopify" />
          <TextField label="Type" value={newDraft.type} onChange={(value) => updateNew("type", value)} placeholder="shopify, etsy, woocommerce" />
          <TextField label="API basis-URL" value={newDraft.api_base_url} onChange={(value) => updateNew("api_base_url", value)} placeholder="Optioneel" />
          <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm font-semibold">
            <input checked={newDraft.active} onChange={(event) => updateNew("active", event.target.checked)} type="checkbox" />
            Actief
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === "new"} type="submit">
            {busyKey === "new" ? "Aanmaken..." : "Kanaal aanmaken"}
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {platforms.map((platform) => {
          const draft = drafts[platform.id] || draftFromPlatform(platform);
          return (
            <details className="rounded-lg border border-line bg-panelSoft p-4" key={platform.id}>
              <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-ink">{platform.name}</div>
                    <div className="mt-1 text-sm text-muted">{platform.type} - {platform.active ? "actief" : "inactief"}</div>
                  </div>
                  <Link className="rounded-md border border-line px-3 py-2 text-sm font-bold text-ink hover:border-brand hover:text-brand" href={`/verkoopkanalen/${platform.id}`}>
                    Credentials beheren
                  </Link>
                </div>
              </summary>
              <div className="mt-4 grid gap-4 border-t border-line pt-4 md:grid-cols-2">
                <TextField label="Naam" value={draft.name} onChange={(value) => updateExisting(platform.id, "name", value)} />
                <TextField label="Type" value={draft.type} onChange={(value) => updateExisting(platform.id, "type", value)} />
                <TextField label="API basis-URL" value={draft.api_base_url} onChange={(value) => updateExisting(platform.id, "api_base_url", value)} />
                <label className="flex items-center gap-3 rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm font-semibold">
                  <input checked={draft.active} onChange={(event) => updateExisting(platform.id, "active", event.target.checked)} type="checkbox" />
                  Actief
                </label>
              </div>
              <div className="mt-4 flex justify-end">
                <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === String(platform.id)} onClick={() => savePlatform(platform.id)} type="button">
                  {busyKey === String(platform.id) ? "Opslaan..." : "Kanaal opslaan"}
                </button>
              </div>
            </details>
          );
        })}
      </div>
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

