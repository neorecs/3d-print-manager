"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { ProductMedia } from "@/lib/types";

const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

function mediaUrl(path?: string | null) {
  if (!path) {
    return "";
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${PUBLIC_API_BASE_URL}${path}`;
}

export function MediaManager({ productId, media }: { productId: number; media: ProductMedia[] }) {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [altText, setAltText] = useState("");
  const [sortOrder, setSortOrder] = useState("0");
  const [primary, setPrimary] = useState(media.length === 0);
  const [drafts, setDrafts] = useState<Record<number, { alt_text: string; sort_order: string; is_primary: boolean }>>(() =>
    Object.fromEntries(
      media.map((item) => [
        item.id,
        {
          alt_text: item.alt_text || "",
          sort_order: String(item.sort_order ?? 0),
          is_primary: Boolean(item.is_primary),
        },
      ]),
    ),
  );

  async function uploadMedia(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploading(true);
    setMessage(null);
    setError(null);

    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement | null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setUploading(false);
      setError("Kies eerst een afbeelding.");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("alt_text", altText);
      formData.append("sort_order", sortOrder || "0");
      formData.append("is_primary", primary ? "true" : "false");

      const response = await fetch(`/api/products/${productId}/media/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Foto uploaden is mislukt");
      }

      form.reset();
      setAltText("");
      setSortOrder("0");
      setPrimary(false);
      setMessage("Foto toegevoegd. Platformpublicaties krijgen synchronisatie nodig.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Foto uploaden is mislukt");
    } finally {
      setUploading(false);
    }
  }

  function updateDraft(id: number, field: "alt_text" | "sort_order" | "is_primary", value: string | boolean) {
    setDrafts((current) => ({
      ...current,
      [id]: {
        alt_text: current[id]?.alt_text || "",
        sort_order: current[id]?.sort_order || "0",
        is_primary: current[id]?.is_primary || false,
        [field]: value,
      },
    }));
  }

  async function saveMedia(item: ProductMedia) {
    setSavingId(item.id);
    setMessage(null);
    setError(null);
    const draft = drafts[item.id] || {
      alt_text: item.alt_text || "",
      sort_order: String(item.sort_order ?? 0),
      is_primary: Boolean(item.is_primary),
    };

    try {
      const response = await fetch(`/api/product-media/${item.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: item.file_path,
          media_type: item.media_type || "image",
          alt_text: draft.alt_text || null,
          sort_order: Number(draft.sort_order || 0),
          is_primary: draft.is_primary,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Foto kon niet worden opgeslagen");
      }

      setMessage("Foto opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Foto opslaan is mislukt");
    } finally {
      setSavingId(null);
    }
  }

  async function deleteMedia(id: number) {
    const confirmed = window.confirm("Weet je zeker dat je deze foto wilt verwijderen?");
    if (!confirmed) {
      return;
    }

    setSavingId(id);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/product-media/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "Foto kon niet worden verwijderd");
      }

      setMessage("Foto verwijderd.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Foto verwijderen is mislukt");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-50 p-4" onSubmit={uploadMedia}>
        <div className="mb-4">
          <h3 className="font-bold text-ink">Foto uploaden</h3>
          <p className="mt-1 text-sm text-muted">Gebruik JPG, PNG, WEBP of GIF. Kies direct of dit de hoofdfoto is.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-700">Afbeelding</span>
            <input
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
              name="file"
              required
              type="file"
            />
          </label>
          <TextField label="Alt-tekst" value={altText} onChange={setAltText} placeholder="Beschrijf wat op de foto staat" />
          <TextField label="Volgorde" value={sortOrder} onChange={setSortOrder} inputMode="numeric" />
          <label className="flex items-center gap-3 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold">
            <input checked={primary} onChange={(event) => setPrimary(event.target.checked)} type="checkbox" />
            Instellen als hoofdfoto
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={uploading}
            type="submit"
          >
            {uploading ? "Uploaden..." : "Foto uploaden"}
          </button>
        </div>
      </form>

      {media.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {media.map((item) => {
            const draft = drafts[item.id] || {
              alt_text: item.alt_text || "",
              sort_order: String(item.sort_order ?? 0),
              is_primary: Boolean(item.is_primary),
            };
            const src = mediaUrl(item.file_path);
            return (
              <article className="rounded-lg border border-line bg-white p-3" key={item.id}>
                <div className="overflow-hidden rounded-md border border-line bg-slate-100">
                  {src ? (
                    <img alt={draft.alt_text || "Productfoto"} className="h-56 w-full object-cover" src={src} />
                  ) : (
                    <div className="flex h-56 items-center justify-center text-sm font-semibold text-muted">Geen afbeelding</div>
                  )}
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="font-bold text-ink">Foto {item.sort_order ?? item.id}</div>
                  {item.is_primary ? <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">Hoofdfoto</span> : null}
                </div>
                <div className="mt-3 grid gap-3">
                  <TextField label="Alt-tekst" value={draft.alt_text} onChange={(value) => updateDraft(item.id, "alt_text", value)} />
                  <TextField label="Volgorde" value={draft.sort_order} onChange={(value) => updateDraft(item.id, "sort_order", value)} inputMode="numeric" />
                  <label className="flex items-center gap-3 rounded-md border border-line bg-slate-50 px-3 py-2 text-sm font-semibold">
                    <input checked={draft.is_primary} onChange={(event) => updateDraft(item.id, "is_primary", event.target.checked)} type="checkbox" />
                    Hoofdfoto
                  </label>
                </div>
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  <button
                    className="rounded-md border border-red-200 bg-white px-3 py-2 text-sm font-bold text-red-700"
                    disabled={savingId === item.id}
                    onClick={() => deleteMedia(item.id)}
                    type="button"
                  >
                    Verwijderen
                  </button>
                  <button
                    className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={savingId === item.id}
                    onClick={() => saveMedia(item)}
                    type="button"
                  >
                    {savingId === item.id ? "Opslaan..." : "Foto opslaan"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
          Nog geen foto's. Upload minimaal een foto voordat je publicatie naar verkoopplatformen voorbereidt.
        </div>
      )}
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
