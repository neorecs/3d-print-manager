"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type RecommendationAction = "accept" | "ignore" | "convert-to-print-job";

export function RecommendationActions({ recommendationId, status, safetyStock, quantity }: { recommendationId: number; status?: string | null; safetyStock: number; quantity: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState<RecommendationAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adjusting, setAdjusting] = useState(false);
  const [adjustedSafety, setAdjustedSafety] = useState(String(safetyStock));
  const [adjustedQuantity, setAdjustedQuantity] = useState(String(quantity));
  const [currentStatus, setCurrentStatus] = useState(status);

  useEffect(() => setCurrentStatus(status), [status]);

  async function run(action: RecommendationAction) {
    setBusy(action);
    setError(null);
    try {
      const response = await fetch(`/api/stock-recommendations/${recommendationId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Voorraadadviesactie is mislukt");
      const completedStatus = action === "accept" ? "geaccepteerd" : action === "ignore" ? "genegeerd" : "omgezet_naar_printtaak";
      setCurrentStatus(data?.recommendation?.status || completedStatus);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Actie mislukt");
    } finally {
      setBusy(null);
    }
  }

  async function adjust() {
    setError(null);
    const nextSafety = Number(adjustedSafety);
    const nextQuantity = Number(adjustedQuantity);
    if (!Number.isInteger(nextSafety) || nextSafety < 0 || !Number.isInteger(nextQuantity) || nextQuantity < 0) {
      setError("Gebruik hele aantallen van nul of hoger.");
      return;
    }
    setBusy("accept");
    try {
      const response = await fetch(`/api/stock-recommendations/${recommendationId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ safety_stock: nextSafety, recommended_print_quantity: nextQuantity, reason: "Handmatig aangepast in Analyse." }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Voorraadadvies aanpassen is mislukt");
      setCurrentStatus(data?.status || "aangepast");
      setAdjusting(false);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Aanpassen is mislukt");
    } finally {
      setBusy(null);
    }
  }

  const mayCreatePrintJob = currentStatus === "geaccepteerd" || currentStatus === "aangepast";

  return (
    <div className="space-y-2">
      {error ? <div className="text-sm font-semibold text-red-300">{error}</div> : null}
      {adjusting ? (
        <div className="grid gap-3 rounded-lg border border-line bg-slate-950/30 p-3 sm:grid-cols-2">
          <label className="text-sm font-bold text-slate-200">Veiligheidsvoorraad
            <input className="mt-1 w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-ink" inputMode="numeric" min="0" onChange={(event) => setAdjustedSafety(event.target.value)} type="number" value={adjustedSafety} />
          </label>
          <label className="text-sm font-bold text-slate-200">Extra printen
            <input className="mt-1 w-full rounded-md border border-line bg-slate-950 px-3 py-2 text-ink" inputMode="numeric" min="0" onChange={(event) => setAdjustedQuantity(event.target.value)} type="number" value={adjustedQuantity} />
          </label>
          <div className="flex gap-2 sm:col-span-2 sm:justify-end">
            <button className="rounded-md border border-line px-3 py-2 text-sm font-bold text-slate-300" disabled={busy !== null} onClick={() => setAdjusting(false)} type="button">Annuleren</button>
            <button className="rounded-md bg-brand px-3 py-2 text-sm font-black text-slate-950" disabled={busy !== null} onClick={adjust} type="button">Wijziging opslaan</button>
          </div>
        </div>
      ) : null}
      <div className="flex flex-wrap justify-end gap-2">
        {currentStatus === "nieuw" ? <button className="rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink font-bold text-slate-300 disabled:opacity-60" disabled={busy !== null} onClick={() => run("accept")} type="button">{busy === "accept" ? "..." : "Accepteren"}</button> : null}
        <button className="rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm font-bold text-slate-300 disabled:opacity-60" disabled={busy !== null} onClick={() => setAdjusting((value) => !value)} type="button">Aanpassen</button>
        <button className="rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink font-bold text-slate-300 disabled:opacity-60" disabled={busy !== null} onClick={() => run("ignore")} type="button">
          {busy === "ignore" ? "..." : "Negeren"}
        </button>
        {mayCreatePrintJob ? <button className="rounded-md bg-brand px-3 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busy !== null} onClick={() => run("convert-to-print-job")} type="button">
          {busy === "convert-to-print-job" ? "..." : "Printtaak maken"}
        </button> : null}
      </div>
    </div>
  );
}

export function GenerateRecommendationsButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/stock-recommendations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period_days: 30, safety_stock: 2, weeks_ahead: 1 }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Advies genereren is mislukt");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Advies genereren is mislukt");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busy} onClick={generate} type="button">
        {busy ? "Genereren..." : "Voorraadadvies genereren"}
      </button>
      {error ? <span className="text-sm font-semibold text-red-300">{error}</span> : null}
    </div>
  );
}
