"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type RecommendationAction = "accept" | "ignore" | "convert-to-print-job";

export function RecommendationActions({ recommendationId }: { recommendationId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState<RecommendationAction | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Actie mislukt");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-2">
      {error ? <div className="text-sm font-semibold text-red-700">{error}</div> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 disabled:opacity-60" disabled={busy !== null} onClick={() => run("accept")} type="button">
          {busy === "accept" ? "..." : "Accepteren"}
        </button>
        <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 disabled:opacity-60" disabled={busy !== null} onClick={() => run("ignore")} type="button">
          {busy === "ignore" ? "..." : "Negeren"}
        </button>
        <button className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy !== null} onClick={() => run("convert-to-print-job")} type="button">
          {busy === "convert-to-print-job" ? "..." : "Printtaak maken"}
        </button>
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
      <button className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy} onClick={generate} type="button">
        {busy ? "Genereren..." : "Voorraadadvies genereren"}
      </button>
      {error ? <span className="text-sm font-semibold text-red-700">{error}</span> : null}
    </div>
  );
}
