"use client";

import { useState } from "react";

export function TestNotificationButton() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function sendTest() {
    setBusy(true);
    setResult(null);
    try {
      const response = await fetch("/api/system/notifications/test", { method: "POST" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Testmelding versturen is mislukt.");
      const channels: { channel: string; status: string; error?: string | null }[] = data?.channels || [];
      setResult(channels.map((item) => `${item.channel}: ${item.status}${item.error ? ` (${item.error})` : ""}`).join(" · ") || "Geen kanaal verstuurd.");
    } catch (caught) {
      setResult(caught instanceof Error ? caught.message : "Testmelding versturen is mislukt.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button className="rounded-md border border-line px-3 py-2 text-sm font-bold text-slate-200 hover:bg-white/5 disabled:opacity-60" disabled={busy} onClick={sendTest} type="button">
        {busy ? "Versturen..." : "Testmelding sturen"}
      </button>
      {result ? <span className="text-sm text-muted">{result}</span> : null}
    </div>
  );
}
