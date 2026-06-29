"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { AccountingFiscalSetting } from "@/lib/types";

export function FiscalSettingsForm({ settings }: { settings: AccountingFiscalSetting[] }) {
  const router = useRouter();
  const initial = Object.fromEntries(settings.map((item) => [item.setting_name, item.value]));
  const [values, setValues] = useState<Record<string, string>>({
    btw_regime: initial.btw_regime || "standaard",
    kor_enabled: initial.kor_enabled || "false",
    default_country: initial.default_country || "NL",
    eu_sales_enabled: initial.eu_sales_enabled || "false",
    default_vat_rate: initial.default_vat_rate || "21",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      await Promise.all(
        Object.entries(values).map(([setting_name, value]) =>
          fetch("/api/accounting/fiscal-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ setting_name, value, note: "Ingesteld via administratie UI." }),
          }).then(async (response) => {
            if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || "Instelling opslaan mislukt");
          }),
        ),
      );
      setMessage("Fiscale instellingen opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Fiscale instellingen opslaan mislukt");
    }
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      {message ? <Notice tone="good" text={message} /> : null}
      {error ? <Notice tone="bad" text={error} /> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <Select label="Btw-regime" value={values.btw_regime} onChange={(value) => setValues({ ...values, btw_regime: value })} options={["standaard", "kor", "marge", "anders"]} />
        <Select label="KOR actief" value={values.kor_enabled} onChange={(value) => setValues({ ...values, kor_enabled: value })} options={["false", "true"]} />
        <Text label="Standaardland" value={values.default_country} onChange={(value) => setValues({ ...values, default_country: value })} />
        <Select label="EU-verkoop actief" value={values.eu_sales_enabled} onChange={(value) => setValues({ ...values, eu_sales_enabled: value })} options={["false", "true"]} />
        <Text label="Standaard btw %" value={values.default_vat_rate} onChange={(value) => setValues({ ...values, default_vat_rate: value })} />
      </div>
      <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950" type="submit">Fiscale instellingen opslaan</button>
    </form>
  );
}

export function VatPeriodCloseForm({ startDate, endDate }: { startDate?: string; endDate?: string }) {
  const router = useRouter();
  const [periodName, setPeriodName] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/accounting/vat-periods/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period_name: periodName, start_date: startDate, end_date: endDate, note: note || null }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Btw-periode afsluiten mislukt");
      setMessage("Btw-periode afgesloten.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Btw-periode afsluiten mislukt");
    }
  }

  const disabled = !startDate || !endDate;
  return (
    <form className="space-y-4" onSubmit={submit}>
      {message ? <Notice tone="good" text={message} /> : null}
      {error ? <Notice tone="bad" text={error} /> : null}
      <div className="grid gap-4 md:grid-cols-[1fr_2fr_auto]">
        <Text label="Periodenaam" value={periodName} onChange={setPeriodName} placeholder="Bijv. 2026-Q2" required />
        <Text label="Notitie" value={note} onChange={setNote} placeholder="Optioneel voor boekhouder" />
        <div className="flex items-end">
          <button className="w-full rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={disabled} type="submit">Periode afsluiten</button>
        </div>
      </div>
      {disabled ? <p className="text-sm text-muted">Kies eerst een vanaf- en einddatum in het periodefilter.</p> : null}
    </form>
  );
}

export function CorrectionButton({ id, type, disabled = false }: { id: number; type: "sale" | "purchase"; disabled?: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function run() {
    const reason = window.prompt(type === "sale" ? "Reden voor creditboeking:" : "Reden voor inkoopcorrectie:");
    if (!reason) return;
    setBusy(true);
    const path = type === "sale" ? `/api/accounting/sales/${id}/credit` : `/api/accounting/purchases/${id}/correction`;
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    setBusy(false);
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      window.alert(data?.detail || "Correctie maken mislukt");
      return;
    }
    router.refresh();
  }
  return (
    <button className="font-bold text-brand hover:text-slate-950 disabled:text-muted" disabled={disabled || busy} onClick={run} type="button">
      {busy ? "Bezig..." : type === "sale" ? "Credit" : "Correctie"}
    </button>
  );
}

export function ArchiveDocumentButton({ id, disabled = false }: { id: number; disabled?: boolean }) {
  const router = useRouter();
  async function run() {
    if (!window.confirm("Document archiveren? Het bestand blijft bewaard, maar telt niet meer als actief document.")) return;
    const response = await fetch(`/api/accounting/documents/${id}/archive`, { method: "POST" });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      window.alert(data?.detail || "Document archiveren mislukt");
      return;
    }
    router.refresh();
  }
  return <button className="font-bold text-brand hover:text-slate-950 disabled:text-muted" disabled={disabled} onClick={run} type="button">Archiveren</button>;
}

function Text({ label, value, onChange, placeholder, required = false }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; required?: boolean }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required={required} value={value} />
    </label>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-300">{label}</span>
      <select className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => onChange(event.target.value)} value={value}>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function Notice({ tone, text }: { tone: "good" | "bad"; text: string }) {
  return <div className={`rounded-md border px-3 py-2 text-sm font-semibold ${tone === "good" ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300" : "border-red-400/25 bg-red-400/10 text-red-300"}`}>{text}</div>;
}
