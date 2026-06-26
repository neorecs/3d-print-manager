"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type OrderAction = "link-items" | "process-inventory" | "create-print-jobs";

const actionLabels: Record<OrderAction, string> = {
  "link-items": "Orderregels koppelen",
  "process-inventory": "Voorraad controleren",
  "create-print-jobs": "Printtaken maken",
};

export function OrderActions({ orderId }: { orderId: number }) {
  const router = useRouter();
  const [busyAction, setBusyAction] = useState<OrderAction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(action: OrderAction) {
    setBusyAction(action);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`/api/orders/${orderId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Orderactie is mislukt");
      }

      setMessage(action === "link-items" ? "Orderregels opnieuw gekoppeld." : action === "process-inventory" ? "Voorraadcontrole uitgevoerd." : "Printtaken aangemaakt of bijgewerkt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Orderactie is mislukt");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="space-y-3">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}
      <div className="flex flex-wrap gap-2">
        {(Object.keys(actionLabels) as OrderAction[]).map((action) => (
          <button
            className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busyAction !== null}
            key={action}
            onClick={() => runAction(action)}
            type="button"
          >
            {busyAction === action ? "Bezig..." : actionLabels[action]}
          </button>
        ))}
      </div>
      <p className="text-sm leading-6 text-muted">
        Volgorde: eerst koppelen op SKU, daarna voorraad controleren, daarna alleen tekorten als printtaken aanmaken.
      </p>
    </div>
  );
}
