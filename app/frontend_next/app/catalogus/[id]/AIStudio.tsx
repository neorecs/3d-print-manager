"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CHANNEL_TYPES } from "@/lib/channels";
import type { Platform, Product, ProductPublication } from "@/lib/types";

type Listing = {
  channel: string;
  title: string;
  description: string;
  tags: string[];
  adjusted: boolean;
  rules: { naam?: string; titel_max_tekens?: number; max_tags?: number; tag_max_tekens?: number };
};

type StudioResult = { listings: Listing[]; notes: string[]; source: string; repaired: boolean; photos_used: number };

type Props = { product: Product; platforms: Platform[]; publications: ProductPublication[] };

export function AIStudio({ product, platforms, publications }: Props) {
  const router = useRouter();
  const linkedTypes = useMemo(() => {
    const byId = new Map(platforms.map((platform) => [platform.id, platform.type.toLowerCase()]));
    return Array.from(new Set(publications.map((publication) => byId.get(publication.platform_id)).filter(Boolean))) as string[];
  }, [platforms, publications]);
  const [channels, setChannels] = useState<string[]>(linkedTypes.length ? linkedTypes : ["etsy"]);
  const [usePhotos, setUsePhotos] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StudioResult | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Listing>>({});
  const [applied, setApplied] = useState<Record<string, string>>({});

  function toggle(channel: string) {
    setChannels((current) => (current.includes(channel) ? current.filter((item) => item !== channel) : [...current, channel]));
  }

  async function generate() {
    setBusy(true);
    setError(null);
    setApplied({});
    try {
      const response = await fetch(`/api/products/${product.id}/ai/listings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channels, use_photos: usePhotos }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Teksten maken mislukt.");
      setResult(data);
      setDrafts(Object.fromEntries((data.listings as Listing[]).map((listing) => [listing.channel, listing])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Teksten maken mislukt.");
    } finally {
      setBusy(false);
    }
  }

  async function apply(channel: string) {
    const draft = drafts[channel];
    setApplied((current) => ({ ...current, [channel]: "bezig" }));
    const response = await fetch(`/api/products/${product.id}/ai/listings/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, title: draft.title, description: draft.description, tags: draft.tags }),
    });
    const data = await response.json().catch(() => ({}));
    setApplied((current) => ({ ...current, [channel]: response.ok ? "overgenomen" : data.detail || "Overnemen mislukt." }));
    if (response.ok) router.refresh();
  }

  function update(channel: string, field: "title" | "description" | "tags", value: string) {
    setDrafts((current) => ({
      ...current,
      [channel]: { ...current[channel], [field]: field === "tags" ? value.split(",").map((tag) => tag.trim()).filter(Boolean) : value },
    }));
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-line bg-surfaceSoft p-4">
        <p className="text-sm text-inkSoft">
          Kies de kanalen. De AI schrijft per kanaal een titel, omschrijving en tags binnen de regels van dat kanaal en kijkt daarbij naar je foto&apos;s.
          Niets wordt opgeslagen voordat je op <strong>Overnemen</strong> klikt.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {CHANNEL_TYPES.map((channel) => (
            <label className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold ${channels.includes(channel.value) ? "border-brand bg-brandSoft text-brand" : "border-line text-inkSoft"}`} key={channel.value}>
              <input checked={channels.includes(channel.value)} className="sr-only" onChange={() => toggle(channel.value)} type="checkbox" />
              {channel.label}
            </label>
          ))}
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm text-inkSoft">
          <input checked={usePhotos} onChange={(event) => setUsePhotos(event.target.checked)} type="checkbox" />
          Foto&apos;s meesturen (maximaal 4, originele foto&apos;s eerst)
        </label>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-onBrand disabled:opacity-60" disabled={busy || channels.length === 0} onClick={generate} type="button">
            {busy ? "Bezig met schrijven..." : result ? "Opnieuw maken" : "Teksten maken"}
          </button>
          {error ? <span className="text-sm font-semibold text-red-700">{error}</span> : null}
        </div>
      </div>

      {result ? (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            {result.source === "voorbeeld" ? "Voorbeeldteksten (AI staat uit)." : `Gemaakt met ${result.source.replace("openai_api:", "")}`}
            {result.photos_used ? ` · ${result.photos_used} foto('s) bekeken` : ""}
            {result.repaired ? " · één herstelronde nodig geweest" : ""}
          </p>
          {result.notes.length ? (
            <div className="rounded-md border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-900">
              <span className="font-semibold">Tips</span>
              <ul className="mt-1 list-disc pl-5">{result.notes.map((note) => <li key={note}>{note}</li>)}</ul>
            </div>
          ) : null}
          {result.listings.map((listing) => {
            const draft = drafts[listing.channel] || listing;
            const titleMax = listing.rules.titel_max_tekens;
            const state = applied[listing.channel];
            return (
              <article className="rounded-lg border border-line bg-panel p-4" key={listing.channel}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-ink">{listing.rules.naam || listing.channel}</h3>
                  {listing.adjusted ? <span className="text-xs font-semibold text-amber-800">ingekort tot de kanaalregels</span> : null}
                </div>
                <label className="mt-3 block space-y-1">
                  <span className="flex justify-between text-sm font-semibold text-inkSoft">Titel<span className="font-normal text-muted">{draft.title.length}{titleMax ? ` / ${titleMax}` : ""}</span></span>
                  <input className="w-full rounded-md border border-line bg-surfaceSoft px-3 py-2 text-sm text-ink outline-none focus:border-brand" maxLength={titleMax || undefined} onChange={(event) => update(listing.channel, "title", event.target.value)} value={draft.title} />
                </label>
                <label className="mt-3 block space-y-1">
                  <span className="text-sm font-semibold text-inkSoft">Omschrijving</span>
                  <textarea className="min-h-40 w-full rounded-md border border-line bg-surfaceSoft px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => update(listing.channel, "description", event.target.value)} value={draft.description} />
                </label>
                <label className="mt-3 block space-y-1">
                  <span className="flex justify-between text-sm font-semibold text-inkSoft">Tags (komma-gescheiden)<span className="font-normal text-muted">{draft.tags.length}{listing.rules.max_tags ? ` / ${listing.rules.max_tags}` : ""}</span></span>
                  <input className="w-full rounded-md border border-line bg-surfaceSoft px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => update(listing.channel, "tags", event.target.value)} value={draft.tags.join(", ")} />
                </label>
                <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
                  {state && state !== "bezig" ? <span className={`text-sm font-semibold ${state === "overgenomen" ? "text-emerald-700" : "text-red-700"}`}>{state === "overgenomen" ? "Overgenomen in de publicatie" : state}</span> : null}
                  <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink hover:border-brand" onClick={() => navigator.clipboard?.writeText(`${draft.title}\n\n${draft.description}\n\n${draft.tags.join(", ")}`)} type="button">Kopiëren</button>
                  <button className="rounded-md bg-brand px-3 py-2 text-sm font-semibold text-onBrand disabled:opacity-60" disabled={state === "bezig"} onClick={() => apply(listing.channel)} type="button">Overnemen</button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
