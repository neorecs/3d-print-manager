"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type SaleDraft = {
  invoice_number: string;
  invoice_date: string;
  customer_name: string;
  customer_country: string;
  description: string;
  net_amount: string;
  vat_rate: string;
  status: string;
  note: string;
};

function emptyDraft(): SaleDraft {
  return {
    invoice_number: "",
    invoice_date: "",
    customer_name: "",
    customer_country: "NL",
    description: "",
    net_amount: "",
    vat_rate: "21",
    status: "concept",
    note: "",
  };
}

function numberOrZero(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function AccountingSaleForm() {
  const router = useRouter();
  const [draft, setDraft] = useState<SaleDraft>(() => emptyDraft());
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof SaleDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch("/api/accounting/sales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invoice_number: draft.invoice_number.trim() || null,
          invoice_date: draft.invoice_date || null,
          customer_name: draft.customer_name.trim() || null,
          customer_country: draft.customer_country.trim() || null,
          description: draft.description.trim() || null,
          net_amount: numberOrZero(draft.net_amount),
          vat_rate: numberOrZero(draft.vat_rate),
          status: draft.status,
          source: "manual",
          note: draft.note.trim() || null,
        }),
      });
      const sale = await response.json().catch(() => null);
      if (!response.ok) throw new Error(sale?.detail || "Verkoopboeking kon niet worden opgeslagen");

      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("document_type", "verkoopfactuur");
        formData.append("sale_id", String(sale.id));
        const uploadResponse = await fetch("/api/accounting/documents/upload", {
          method: "POST",
          body: formData,
        });
        const upload = await uploadResponse.json().catch(() => null);
        if (!uploadResponse.ok) throw new Error(upload?.detail || "Factuur uploaden is mislukt");
      }

      setDraft(emptyDraft());
      setFile(null);
      setMessage(file ? "Verkoopboeking en factuur opgeslagen." : "Verkoopboeking opgeslagen. Koppel later nog een factuur als dat nodig is.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verkoopboeking opslaan is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <TextField label="Factuurnummer" value={draft.invoice_number} onChange={(value) => update("invoice_number", value)} placeholder="Bijv. FAC-2026-0001" />
        <TextField label="Factuurdatum" value={draft.invoice_date} onChange={(value) => update("invoice_date", value)} type="date" />
        <TextField label="Klant" value={draft.customer_name} onChange={(value) => update("customer_name", value)} placeholder="Naam klant of verkoopkanaal" />
        <TextField label="Land" value={draft.customer_country} onChange={(value) => update("customer_country", value)} placeholder="NL" />
        <TextField label="Netto bedrag excl. btw" value={draft.net_amount} onChange={(value) => update("net_amount", value)} inputMode="decimal" placeholder="Bijv. 16,45" required />
        <TextField label="Btw percentage" value={draft.vat_rate} onChange={(value) => update("vat_rate", value)} inputMode="decimal" />
        <SelectField label="Status" value={draft.status} onChange={(value) => update("status", value)} options={["concept", "geboekt", "betaald", "geannuleerd"]} />
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-300">Factuur of bewijs</span>
          <input
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            type="file"
          />
        </label>
      </div>

      <TextArea label="Omschrijving" value={draft.description} onChange={(value) => update("description", value)} placeholder="Bijv. Handmatige verkoop, marktplaatsverkoop of correctie" />
      <TextArea label="Notitie" value={draft.note} onChange={(value) => update("note", value)} placeholder="Bij twijfel: noteer waarom je deze verkoop handmatig boekt." />

      <div className="flex justify-end">
        <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busy} type="submit">
          {busy ? "Opslaan..." : "Verkoopboeking opslaan"}
        </button>
      </div>
    </form>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  inputMode,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "decimal";
  type?: "text" | "date";
  required?: boolean;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand"
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}

function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <select className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function TextArea({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <textarea
        className="min-h-24 w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}

