"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { AccountingSale } from "@/lib/types";

type OrderAction = "link-items" | "process-inventory" | "create-print-jobs" | "create-accounting-sale";

const actionLabels: Record<OrderAction, string> = {
  "link-items": "Orderregels koppelen",
  "process-inventory": "Voorraad controleren",
  "create-print-jobs": "Printtaken maken",
  "create-accounting-sale": "Verkoopboeking maken",
};

export function OrderActions({ orderId, accountingSale }: { orderId: number; accountingSale?: AccountingSale | null }) {
  const router = useRouter();
  const [busyAction, setBusyAction] = useState<OrderAction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(action: OrderAction) {
    setBusyAction(action);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(action === "create-accounting-sale" ? `/api/orders/${orderId}/create-accounting-sale` : `/api/orders/${orderId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Orderactie is mislukt");
      }

      setMessage(
        action === "link-items"
          ? "Orderregels opnieuw gekoppeld."
          : action === "process-inventory"
            ? "Voorraadcontrole uitgevoerd."
            : action === "create-print-jobs"
              ? "Printtaken aangemaakt of bijgewerkt."
              : data?.message || "Verkoopboeking aangemaakt of gevonden.",
      );
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Orderactie is mislukt");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="space-y-3">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}
      {accountingSale ? (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800">
          Verkoopboeking #{accountingSale.id} bestaat al: {accountingSale.invoice_number || "zonder factuurnummer"}.
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {(Object.keys(actionLabels) as OrderAction[]).map((action) => (
          <button
            className="rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink font-bold text-slate-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busyAction !== null || (action === "create-accounting-sale" && Boolean(accountingSale))}
            key={action}
            onClick={() => runAction(action)}
            type="button"
          >
            {busyAction === action ? "Bezig..." : actionLabels[action]}
          </button>
        ))}
      </div>
      <p className="text-sm leading-6 text-muted">
        Volgorde: eerst koppelen op SKU, daarna voorraad controleren, daarna alleen tekorten als printtaken aanmaken. Maak daarna de verkoopboeking voor de administratie.
      </p>
      <p className="text-xs leading-5 text-muted">
        Administratie: de automatische boeking gebruikt voorlopig 21% btw inclusief orderbedrag. Controleer dit later per platform, land en btw-regime.
      </p>
    </div>
  );
}
