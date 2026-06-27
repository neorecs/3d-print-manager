"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type PurchaseDraft = {
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  category: string;
  description: string;
  net_amount: string;
  vat_rate: string;
  payment_status: string;
  note: string;
};

function emptyDraft(): PurchaseDraft {
  return {
    supplier_name: "",
    invoice_number: "",
    invoice_date: "",
    category: "filament",
    description: "",
    net_amount: "",
    vat_rate: "21",
    payment_status: "betaald",
    note: "",
  };
}

function numberOrZero(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function AccountingPurchaseForm() {
  const router = useRouter();
  const [draft, setDraft] = useState<PurchaseDraft>(() => emptyDraft());
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof PurchaseDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch("/api/accounting/purchases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: draft.supplier_name.trim(),
          invoice_number: draft.invoice_number.trim() || null,
          invoice_date: draft.invoice_date || null,
          category: draft.category,
          description: draft.description.trim() || null,
          net_amount: numberOrZero(draft.net_amount),
          vat_rate: numberOrZero(draft.vat_rate),
          payment_status: draft.payment_status,
          note: draft.note.trim() || null,
        }),
      });
      const purchase = await response.json().catch(() => null);
      if (!response.ok) throw new Error(purchase?.detail || "Inkoopboeking kon niet worden opgeslagen");

      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("document_type", "inkoopfactuur");
        formData.append("purchase_id", String(purchase.id));
        const uploadResponse = await fetch("/api/accounting/documents/upload", {
          method: "POST",
          body: formData,
        });
        const upload = await uploadResponse.json().catch(() => null);
        if (!uploadResponse.ok) throw new Error(upload?.detail || "Bon/factuur uploaden is mislukt");
      }

      setDraft(emptyDraft());
      setFile(null);
      setMessage(file ? "Inkoopboeking en document opgeslagen." : "Inkoopboeking opgeslagen. Koppel later nog een bon of factuur.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Inkoopboeking opslaan is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <TextField label="Leverancier" value={draft.supplier_name} onChange={(value) => update("supplier_name", value)} placeholder="Bijv. Bambu Lab, Amazon, PostNL" required />
        <TextField label="Factuurnummer" value={draft.invoice_number} onChange={(value) => update("invoice_number", value)} placeholder="Optioneel" />
        <TextField label="Factuurdatum" value={draft.invoice_date} onChange={(value) => update("invoice_date", value)} type="date" />
        <SelectField label="Categorie" value={draft.category} onChange={(value) => update("category", value)} options={["filament", "verpakking", "printeronderdelen", "verzending", "software", "platformkosten", "overig"]} />
        <TextField label="Netto bedrag excl. btw" value={draft.net_amount} onChange={(value) => update("net_amount", value)} inputMode="decimal" placeholder="Bijv. 24,95" required />
        <TextField label="Btw percentage" value={draft.vat_rate} onChange={(value) => update("vat_rate", value)} inputMode="decimal" />
        <SelectField label="Betaalstatus" value={draft.payment_status} onChange={(value) => update("payment_status", value)} options={["betaald", "open", "onbekend"]} />
        <label className="space-y-2">
          <span className="text-sm font-bold text-slate-700">Bon of factuur</span>
          <input
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            type="file"
          />
        </label>
      </div>

      <TextArea label="Omschrijving" value={draft.description} onChange={(value) => update("description", value)} placeholder="Bijv. 2 rollen PLA rood + verzendkosten" />
      <TextArea label="Notitie" value={draft.note} onChange={(value) => update("note", value)} placeholder="Interne notitie voor jezelf of boekhouder" />

      <div className="flex justify-end">
        <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy} type="submit">
          {busy ? "Opslaan..." : "Inkoopboeking opslaan"}
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
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
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
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand" value={value} onChange={(event) => onChange(event.target.value)}>
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
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <textarea
        className="min-h-24 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}
