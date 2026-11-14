"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function MarkPlacedForm({ publicationId, placed, externalUrl }: { publicationId: number; placed: boolean; externalUrl?: string | null }) {
  const router = useRouter();
  const [url, setUrl] = useState(externalUrl || "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/product-publications/${publicationId}/mark-placed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ external_url: url.trim() || null }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Opslaan is mislukt.");
      setMessage("Gemarkeerd als geplaatst.");
      router.refresh();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Opslaan is mislukt.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
      <label className="flex min-w-0 flex-1 basis-72 flex-col gap-1.5 text-sm font-medium text-ink">
        Link naar de geplaatste advertentie (optioneel)
        <input className="min-h-10 rounded-lg border border-line bg-panel px-3 text-sm font-normal text-ink outline-none focus:border-brand" onChange={(event) => setUrl(event.target.value)} placeholder="https://" type="url" value={url} />
      </label>
      <button className="min-h-10 rounded-lg border border-brand bg-brand px-4 text-sm font-semibold text-onBrand disabled:opacity-60" disabled={busy} type="submit">
        {busy ? "Opslaan..." : placed ? "Link bijwerken" : "Markeer als geplaatst"}
      </button>
      {message ? <span className="text-sm text-muted">{message}</span> : null}
    </form>
  );
}
