"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import type { Platform, Product, ProductPublication } from "@/lib/types";

type PublicationDraft = {
  platform_id: string;
  publication_status: string;
  external_product_id: string;
  external_listing_id: string;
  platform_title: string;
  platform_description: string;
  platform_category: string;
  platform_tags: string;
  platform_price_override: string;
  platform_shipping_profile_id: string;
  last_error: string;
};

type PublicationCheck = {
  ready?: boolean;
  valid?: boolean;
  errors?: string[];
  warnings?: string[];
  market_checks?: Array<{
    country_code: string;
    country_name: string;
    language_code: string;
    severity: string;
    message: string;
  }>;
  required_fields_missing?: string[];
  detail?: string;
};

const publicationStatuses = [
  "niet_gepubliceerd",
  "concept",
  "klaar_voor_publicatie",
  "gepubliceerd",
  "synchronisatie_nodig",
  "fout",
  "gepauzeerd",
  "gearchiveerd",
];

function emptyDraft(product: Product, platforms: Platform[]): PublicationDraft {
  return {
    platform_id: platforms[0]?.id ? String(platforms[0].id) : "",
    publication_status: "niet_gepubliceerd",
    external_product_id: "",
    external_listing_id: "",
    platform_title: product.internal_title || product.name || "",
    platform_description: product.sales_description || product.short_description || "",
    platform_category: product.internal_category || "",
    platform_tags: "",
    platform_price_override: "",
    platform_shipping_profile_id: "",
    last_error: "",
  };
}

function draftFromPublication(publication: ProductPublication): PublicationDraft {
  return {
    platform_id: String(publication.platform_id),
    publication_status: publication.publication_status || "niet_gepubliceerd",
    external_product_id: publication.external_product_id || "",
    external_listing_id: publication.external_listing_id || "",
    platform_title: publication.platform_title || "",
    platform_description: publication.platform_description || "",
    platform_category: publication.platform_category || "",
    platform_tags: publication.platform_tags || "",
    platform_price_override: publication.platform_price_override === null || publication.platform_price_override === undefined ? "" : String(publication.platform_price_override),
    platform_shipping_profile_id: publication.platform_shipping_profile_id || "",
    last_error: publication.last_error || "",
  };
}

function toPayload(draft: PublicationDraft) {
  return {
    platform_id: Number(draft.platform_id),
    external_product_id: draft.external_product_id || null,
    external_listing_id: draft.external_listing_id || null,
    publication_status: draft.publication_status,
    platform_title: draft.platform_title || null,
    platform_description: draft.platform_description || null,
    platform_category: draft.platform_category || null,
    platform_tags: draft.platform_tags || null,
    platform_price_override: draft.platform_price_override ? Number(draft.platform_price_override.replace(",", ".")) : null,
    platform_shipping_profile_id: draft.platform_shipping_profile_id || null,
    last_error: draft.last_error || null,
  };
}

function platformName(platforms: Platform[], id: number) {
  const platform = platforms.find((item) => item.id === id);
  return platform ? `${platform.name} (${platform.type})` : `Platform ${id}`;
}

export function PublicationManager({
  product,
  platforms,
  publications,
}: {
  product: Product;
  platforms: Platform[];
  publications: ProductPublication[];
}) {
  const router = useRouter();
  const [newDraft, setNewDraft] = useState<PublicationDraft>(() => emptyDraft(product, platforms));
  const [drafts, setDrafts] = useState<Record<number, PublicationDraft>>(() =>
    Object.fromEntries(publications.map((publication) => [publication.id, draftFromPublication(publication)])),
  );
  const [checks, setChecks] = useState<Record<number, PublicationCheck>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateNew(field: keyof PublicationDraft, value: string) {
    setNewDraft((current) => ({ ...current, [field]: value }));
  }

  function updateExisting(id: number, field: keyof PublicationDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  async function createPublication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingKey("new");
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/products/${product.id}/publications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(newDraft)),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Publicatie kon niet worden aangemaakt");
      }

      setNewDraft(emptyDraft(product, platforms));
      setMessage("Platformpublicatie aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Publicatie opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  async function savePublication(id: number) {
    setSavingKey(String(id));
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/product-publications/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(drafts[id])),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Publicatie kon niet worden opgeslagen");
      }

      setMessage("Platformpublicatie opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Publicatie opslaan is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  async function runCheck(id: number) {
    setSavingKey(`check-${id}`);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/product-publications/${id}/check`);
      const data = (await response.json()) as PublicationCheck;
      if (!response.ok) {
        throw new Error(data.detail || "Publicatiecontrole is mislukt");
      }
      setChecks((current) => ({ ...current, [id]: data }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Publicatiecontrole is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  async function runAction(id: number, action: "publish" | "sync" | "pause") {
    setSavingKey(`${action}-${id}`);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/product-publications/${id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || `${action} is mislukt`);
      }

      setMessage(action === "pause" ? "Publicatie gepauzeerd." : "Publicatieactie uitgevoerd.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Publicatieactie is mislukt");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-50 p-4" onSubmit={createPublication}>
        <div className="mb-4">
          <h3 className="font-bold text-ink">Platformpublicatie toevoegen</h3>
          <p className="mt-1 text-sm text-muted">Maak een Etsy-, Shopify- of andere platformkoppeling voor dit interne product.</p>
        </div>
        {platforms.length ? (
          <>
            <PublicationFields draft={newDraft} platforms={platforms} onChange={updateNew} />
            <div className="mt-4 flex justify-end">
              <button
                className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={savingKey === "new" || !newDraft.platform_id}
                type="submit"
              >
                {savingKey === "new" ? "Aanmaken..." : "Publicatie aanmaken"}
              </button>
            </div>
          </>
        ) : (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            Maak eerst een platform aan voordat je publicaties kunt koppelen.
          </div>
        )}
      </form>

      <div className="space-y-3">
        {publications.length ? (
          publications.map((publication) => {
            const draft = drafts[publication.id] || draftFromPublication(publication);
            const check = checks[publication.id];
            return (
              <details className="rounded-lg border border-line bg-white p-4" key={publication.id}>
                <summary className="cursor-pointer list-none">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-bold text-ink">{platformName(platforms, publication.platform_id)}</div>
                      <div className="mt-1 text-sm text-muted">{publication.platform_title || product.internal_title || product.name}</div>
                    </div>
                    <StatusBadge status={publication.publication_status} />
                  </div>
                </summary>
                <div className="mt-4 border-t border-line pt-4">
                  <PublicationFields
                    draft={draft}
                    platforms={platforms}
                    onChange={(field, value) => updateExisting(publication.id, field, value)}
                  />
                  {check ? <CheckResult check={check} /> : null}
                  {publication.last_error ? <p className="mt-3 text-sm font-semibold text-red-700">{publication.last_error}</p> : null}
                  <div className="mt-4 flex flex-wrap justify-end gap-2">
                    <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700" disabled={savingKey === `check-${publication.id}`} onClick={() => runCheck(publication.id)} type="button">
                      Controleer
                    </button>
                    <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700" disabled={savingKey === `pause-${publication.id}`} onClick={() => runAction(publication.id, "pause")} type="button">
                      Pauzeren
                    </button>
                    <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700" disabled={savingKey === `sync-${publication.id}`} onClick={() => runAction(publication.id, "sync")} type="button">
                      Sync
                    </button>
                    <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700" disabled={savingKey === `publish-${publication.id}`} onClick={() => runAction(publication.id, "publish")} type="button">
                      Publiceren
                    </button>
                    <button className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={savingKey === String(publication.id)} onClick={() => savePublication(publication.id)} type="button">
                      {savingKey === String(publication.id) ? "Opslaan..." : "Opslaan"}
                    </button>
                  </div>
                </div>
              </details>
            );
          })
        ) : (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
            Nog geen platformpublicaties. Voeg hierboven de eerste platformkoppeling toe.
          </div>
        )}
      </div>
    </div>
  );
}

function PublicationFields({
  draft,
  platforms,
  onChange,
}: {
  draft: PublicationDraft;
  platforms: Platform[];
  onChange: (field: keyof PublicationDraft, value: string) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="space-y-2">
        <span className="text-sm font-bold text-slate-700">Platform</span>
        <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand" value={draft.platform_id} onChange={(event) => onChange("platform_id", event.target.value)}>
          {platforms.map((platform) => (
            <option key={platform.id} value={platform.id}>{platform.name} ({platform.type})</option>
          ))}
        </select>
      </label>
      <label className="space-y-2">
        <span className="text-sm font-bold text-slate-700">Publicatiestatus</span>
        <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand" value={draft.publication_status} onChange={(event) => onChange("publication_status", event.target.value)}>
          {publicationStatuses.map((status) => (
            <option key={status} value={status}>{status.replace(/_/g, " ")}</option>
          ))}
        </select>
      </label>
      <TextField label="Platformtitel" value={draft.platform_title} onChange={(value) => onChange("platform_title", value)} />
      <TextField label="Platformcategorie" value={draft.platform_category} onChange={(value) => onChange("platform_category", value)} />
      <TextField label="Tags" value={draft.platform_tags} onChange={(value) => onChange("platform_tags", value)} placeholder="Komma-gescheiden tags" />
      <TextField label="Prijs override" value={draft.platform_price_override} onChange={(value) => onChange("platform_price_override", value)} inputMode="decimal" />
      <TextField label="Verzendprofiel ID" value={draft.platform_shipping_profile_id} onChange={(value) => onChange("platform_shipping_profile_id", value)} />
      <TextField label="Extern product/listing ID" value={draft.external_product_id} onChange={(value) => onChange("external_product_id", value)} />
      <TextField label="Extern listing ID" value={draft.external_listing_id} onChange={(value) => onChange("external_listing_id", value)} />
      <TextField label="Laatste foutmelding" value={draft.last_error} onChange={(value) => onChange("last_error", value)} />
      <label className="space-y-2 md:col-span-2">
        <span className="text-sm font-bold text-slate-700">Platformomschrijving</span>
        <textarea
          className="min-h-32 w-full resize-y rounded-md border border-line bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-brand"
          onChange={(event) => onChange("platform_description", event.target.value)}
          value={draft.platform_description}
        />
      </label>
    </div>
  );
}

function CheckResult({ check }: { check: PublicationCheck }) {
  const errors = check.errors || check.required_fields_missing || [];
  const warnings = check.warnings || [];
  const ready = check.ready ?? check.valid ?? false;
  const marketChecks = check.market_checks || [];
  return (
    <div className={`mt-4 rounded-md border px-3 py-3 text-sm ${ready ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
      <div className="font-bold">{ready ? "Publicatiecontrole geslaagd" : "Publicatiecontrole vraagt aandacht"}</div>
      {errors.length ? <ul className="mt-2 list-disc space-y-1 pl-5">{errors.map((item) => <li key={item}>{item}</li>)}</ul> : null}
      {warnings.length ? <ul className="mt-2 list-disc space-y-1 pl-5">{warnings.map((item) => <li key={item}>{item}</li>)}</ul> : null}
      {marketChecks.length ? (
        <div className="mt-3 rounded-md border border-white/70 bg-white/60 p-3">
          <div className="font-bold">Doellanden en talen</div>
          <ul className="mt-2 space-y-1">
            {marketChecks.map((item) => (
              <li key={`${item.country_code}-${item.language_code}`} className={item.severity === "error" ? "font-semibold text-red-700" : item.severity === "warning" ? "font-semibold text-amber-800" : "text-emerald-800"}>
                {item.country_code} / {item.language_code}: {item.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
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
