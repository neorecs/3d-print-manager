"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import { formatMinutes } from "@/lib/api";
import type { Order, OrderItem, PrintBatch, PrintJob, Product, ProductVariant } from "@/lib/types";

type JobDraft = {
  quantity_needed: string;
  quantity_planned: string;
  quantity_succeeded: string;
  quantity_failed: string;
  quantity_to_order: string;
  quantity_to_inventory: string;
  estimated_print_time_minutes: string;
  estimated_filament_grams: string;
  status: string;
};

type CompleteDraft = {
  quantity_succeeded: string;
  quantity_failed: string;
  quantity_to_order: string;
};

type BatchExportResult = {
  status?: string;
  export_dir?: string;
  row_count?: number;
  files?: Record<string, string>;
};

const printJobStatuses = ["nieuw", "gepland", "bezig", "geprint", "deels_mislukt", "mislukt", "verwerkt", "geannuleerd"];

function valueToString(value?: number | null) {
  return value === null || value === undefined ? "" : String(value);
}

function numberOrZero(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function nullableNumber(value: string) {
  return value.trim() ? numberOrZero(value) : null;
}

function jobDraft(job: PrintJob): JobDraft {
  return {
    quantity_needed: valueToString(job.quantity_needed),
    quantity_planned: valueToString(job.quantity_planned),
    quantity_succeeded: valueToString(job.quantity_succeeded),
    quantity_failed: valueToString(job.quantity_failed),
    quantity_to_order: valueToString(job.quantity_to_order),
    quantity_to_inventory: valueToString(job.quantity_to_inventory),
    estimated_print_time_minutes: valueToString(job.estimated_print_time_minutes),
    estimated_filament_grams: valueToString(job.estimated_filament_grams),
    status: job.status || "nieuw",
  };
}

function completeDraft(job: PrintJob): CompleteDraft {
  return {
    quantity_succeeded: valueToString(job.quantity_succeeded || job.quantity_planned || job.quantity_needed),
    quantity_failed: valueToString(job.quantity_failed || 0),
    quantity_to_order: valueToString(job.quantity_to_order || Math.min(job.quantity_planned || job.quantity_needed || 0, job.quantity_needed || 0)),
  };
}

function variantLabel(variant?: ProductVariant) {
  if (!variant) {
    return "Onbekende variant";
  }

  return [variant.variant_name || `Variant ${variant.id}`, variant.sku, variant.material, variant.color].filter(Boolean).join(" - ");
}

function toJobPayload(job: PrintJob, draft: JobDraft) {
  return {
    order_item_id: job.order_item_id || null,
    product_id: job.product_id,
    product_variant_id: job.product_variant_id,
    color: job.color || null,
    material: job.material || null,
    quantity_needed: numberOrZero(draft.quantity_needed),
    quantity_planned: numberOrZero(draft.quantity_planned),
    quantity_succeeded: numberOrZero(draft.quantity_succeeded),
    quantity_failed: numberOrZero(draft.quantity_failed),
    quantity_to_order: numberOrZero(draft.quantity_to_order),
    quantity_to_inventory: numberOrZero(draft.quantity_to_inventory),
    estimated_print_time_minutes: nullableNumber(draft.estimated_print_time_minutes),
    estimated_filament_grams: nullableNumber(draft.estimated_filament_grams),
    status: draft.status,
  };
}

export function PrintPlanningManager({
  printJobs,
  printBatches,
  products,
  variants,
  orders,
  orderItems,
}: {
  printJobs: PrintJob[];
  printBatches: PrintBatch[];
  products: Product[];
  variants: ProductVariant[];
  orders: Order[];
  orderItems: OrderItem[];
}) {
  const router = useRouter();
  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products]);
  const variantById = useMemo(() => new Map(variants.map((variant) => [variant.id, variant])), [variants]);
  const itemById = useMemo(() => new Map(orderItems.map((item) => [item.id, item])), [orderItems]);
  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);
  const [drafts, setDrafts] = useState<Record<number, JobDraft>>(() => Object.fromEntries(printJobs.map((job) => [job.id, jobDraft(job)])));
  const [completeDrafts, setCompleteDrafts] = useState<Record<number, CompleteDraft>>(() =>
    Object.fromEntries(printJobs.map((job) => [job.id, completeDraft(job)])),
  );
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<BatchExportResult | null>(null);

  const openJobs = printJobs.filter((job) => !["verwerkt", "geannuleerd"].includes(job.status || ""));
  const groups = useMemo(() => {
    const grouped = new Map<string, { material: string; color: string; jobs: PrintJob[]; minutes: number; filament: number; quantity: number }>();
    openJobs
      .filter((job) => ["nieuw", "gepland"].includes(job.status || "nieuw"))
      .forEach((job) => {
        const material = job.material || variantById.get(job.product_variant_id)?.material || "onbekend";
        const color = job.color || variantById.get(job.product_variant_id)?.color || "onbekend";
        const key = `${material}|${color}`;
        const group = grouped.get(key) || { material, color, jobs: [], minutes: 0, filament: 0, quantity: 0 };
        const quantity = job.quantity_planned || job.quantity_needed || 1;
        group.jobs.push(job);
        group.quantity += quantity;
        group.minutes += Number(job.estimated_print_time_minutes || 0) * quantity;
        group.filament += Number(job.estimated_filament_grams || 0) * quantity;
        grouped.set(key, group);
      });
    return Array.from(grouped.values()).sort((a, b) => b.jobs.length - a.jobs.length || a.material.localeCompare(b.material));
  }, [openJobs, variantById]);

  function updateDraft(id: number, field: keyof JobDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  function updateCompleteDraft(id: number, field: keyof CompleteDraft, value: string) {
    setCompleteDrafts((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  async function saveJob(job: PrintJob) {
    setBusyKey(`save-${job.id}`);
    setMessage(null);
    setError(null);
    setExportResult(null);

    try {
      const response = await fetch(`/api/print-jobs/${job.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toJobPayload(job, drafts[job.id])),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Printtaak kon niet worden opgeslagen");
      }

      setMessage("Printtaak opgeslagen.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printtaak opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function completeJob(job: PrintJob) {
    setBusyKey(`complete-${job.id}`);
    setMessage(null);
    setError(null);
    setExportResult(null);

    try {
      const draft = completeDrafts[job.id];
      const response = await fetch(`/api/print-jobs/${job.id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quantity_succeeded: numberOrZero(draft.quantity_succeeded),
          quantity_failed: numberOrZero(draft.quantity_failed),
          quantity_to_order: numberOrZero(draft.quantity_to_order),
        }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Printresultaat kon niet worden verwerkt");
      }

      setMessage("Printresultaat verwerkt. Extra gelukte prints zijn naar vrije voorraad geboekt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Printresultaat verwerken is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function createBatch(group: { material: string; color: string; jobs: PrintJob[] }) {
    setBusyKey(`batch-${group.material}-${group.color}`);
    setMessage(null);
    setError(null);
    setExportResult(null);

    try {
      const response = await fetch("/api/print-batches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          batch_name: `${group.material} - ${group.color}`,
          planned_date: null,
          material: group.material,
          color: group.color,
          print_job_ids: group.jobs.map((job) => job.id),
        }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Batch kon niet worden aangemaakt");
      }

      setMessage("Printbatch aangemaakt.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Batch aanmaken is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function exportBatch(batch: PrintBatch) {
    setBusyKey(`export-${batch.id}`);
    setMessage(null);
    setError(null);
    setExportResult(null);

    try {
      const response = await fetch(`/api/print-batches/${batch.id}/export`, { method: "POST" });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Batch-export is mislukt");
      }

      setExportResult(data);
      setMessage("Batch-export gemaakt voor Bambu Studio.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Batch-export is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-6">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}
      {exportResult ? (
        <div className="rounded-md border border-brand/30 bg-teal-50 px-3 py-3 text-sm text-teal-900">
          <div className="font-bold">Exportmap: {exportResult.export_dir || "-"}</div>
          <div className="mt-1">Regels: {exportResult.row_count ?? "-"}</div>
        </div>
      ) : null}

      <section className="space-y-3">
        <div>
          <h3 className="text-lg font-bold text-ink">Batchadvies op kleur en materiaal</h3>
          <p className="mt-1 text-sm text-muted">Maak batches van open printtaken met dezelfde kleur en hetzelfde materiaal.</p>
        </div>
        {groups.length ? (
          <div className="grid gap-3 xl:grid-cols-2">
            {groups.map((group) => (
              <div className="rounded-lg border border-line bg-white p-4" key={`${group.material}-${group.color}`}>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="font-bold text-ink">{group.material} - {group.color}</div>
                    <p className="mt-1 text-sm text-muted">
                      {group.jobs.length} taken, {group.quantity} stuks, {group.minutes ? formatMinutes(group.minutes) : "printtijd onbekend"}, {group.filament || 0}g filament.
                    </p>
                  </div>
                  <button
                    className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={busyKey !== null}
                    onClick={() => createBatch(group)}
                    type="button"
                  >
                    {busyKey === `batch-${group.material}-${group.color}` ? "Aanmaken..." : "Batch maken"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-line bg-slate-50 px-4 py-3 text-sm font-semibold text-muted">
            Geen open taken die geschikt zijn voor batchadvies.
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-lg font-bold text-ink">Printtaken beheren</h3>
          <p className="mt-1 text-sm text-muted">Wijzig planning/status of verwerk het resultaat na het printen.</p>
        </div>
        {printJobs.length ? (
          <div className="space-y-3">
            {printJobs.map((job) => {
              const draft = drafts[job.id] || jobDraft(job);
              const completion = completeDrafts[job.id] || completeDraft(job);
              const product = productById.get(job.product_id);
              const variant = variantById.get(job.product_variant_id);
              const orderItem = job.order_item_id ? itemById.get(job.order_item_id) : null;
              const order = orderItem ? orderById.get(orderItem.order_id) : null;

              return (
                <details className="rounded-lg border border-line bg-white p-4 shadow-card" key={job.id}>
                  <summary className="cursor-pointer list-none">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="font-bold text-ink">Printtaak #{job.id}</div>
                        <p className="mt-1 text-sm text-muted">
                          {product?.internal_title || product?.name || `Product ${job.product_id}`} - {variantLabel(variant)}
                        </p>
                        <p className="mt-1 text-sm text-muted">
                          {order ? `Order ${order.internal_order_number}` : "Voorraadproductie"} - {job.material || variant?.material || "-"} / {job.color || variant?.color || "-"}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={job.status} />
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                          {job.quantity_planned || job.quantity_needed} stuks
                        </span>
                      </div>
                    </div>
                  </summary>
                  <div className="mt-4 border-t border-line pt-4">
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <NumberField label="Nodig" value={draft.quantity_needed} onChange={(value) => updateDraft(job.id, "quantity_needed", value)} />
                      <NumberField label="Gepland" value={draft.quantity_planned} onChange={(value) => updateDraft(job.id, "quantity_planned", value)} />
                      <NumberField label="Printtijd minuten" value={draft.estimated_print_time_minutes} onChange={(value) => updateDraft(job.id, "estimated_print_time_minutes", value)} />
                      <NumberField label="Filament gram" value={draft.estimated_filament_grams} onChange={(value) => updateDraft(job.id, "estimated_filament_grams", value)} />
                      <label className="space-y-2">
                        <span className="text-sm font-bold text-slate-700">Status</span>
                        <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand" value={draft.status} onChange={(event) => updateDraft(job.id, "status", event.target.value)}>
                          {printJobStatuses.map((status) => (
                            <option key={status} value={status}>{status.replace(/_/g, " ")}</option>
                          ))}
                        </select>
                      </label>
                    </div>

                    <div className="mt-4 flex justify-end">
                      <button
                        className="rounded-md bg-brand px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={busyKey !== null}
                        onClick={() => saveJob(job)}
                        type="button"
                      >
                        {busyKey === `save-${job.id}` ? "Opslaan..." : "Printtaak opslaan"}
                      </button>
                    </div>

                    <div className="mt-5 rounded-lg border border-line bg-slate-50 p-4">
                      <h4 className="font-bold text-ink">Printresultaat verwerken</h4>
                      <p className="mt-1 text-sm text-muted">Gelukte extra prints gaan naar vrije voorraad. Mislukte prints worden traceerbaar geregistreerd.</p>
                      <div className="mt-4 grid gap-4 md:grid-cols-3">
                        <NumberField label="Gelukt" value={completion.quantity_succeeded} onChange={(value) => updateCompleteDraft(job.id, "quantity_succeeded", value)} />
                        <NumberField label="Mislukt" value={completion.quantity_failed} onChange={(value) => updateCompleteDraft(job.id, "quantity_failed", value)} />
                        <NumberField label="Naar order" value={completion.quantity_to_order} onChange={(value) => updateCompleteDraft(job.id, "quantity_to_order", value)} />
                      </div>
                      <div className="mt-4 flex justify-end">
                        <button
                          className="rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={busyKey !== null}
                          onClick={() => completeJob(job)}
                          type="button"
                        >
                          {busyKey === `complete-${job.id}` ? "Verwerken..." : "Resultaat verwerken"}
                        </button>
                      </div>
                    </div>
                  </div>
                </details>
              );
            })}
          </div>
        ) : (
          <div className="rounded-md border border-line bg-slate-50 px-4 py-3 text-sm font-semibold text-muted">
            Nog geen printtaken. Maak ze vanuit een order met voorraadtekort of later vanuit voorraadadvies.
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-lg font-bold text-ink">Printbatches</h3>
          <p className="mt-1 text-sm text-muted">Export maakt productielijsten voor gebruik naast Bambu Studio.</p>
        </div>
        {printBatches.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch</th>
                  <th>Materiaal</th>
                  <th>Kleur</th>
                  <th>Status</th>
                  <th className="text-right">Printtijd</th>
                  <th className="text-right">Filament</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {printBatches.map((batch) => (
                  <tr key={batch.id}>
                    <td className="font-semibold">{batch.batch_name}</td>
                    <td>{batch.material || "-"}</td>
                    <td>{batch.color || "-"}</td>
                    <td><StatusBadge status={batch.status} /></td>
                    <td className="text-right">{batch.estimated_total_print_time_minutes ? formatMinutes(batch.estimated_total_print_time_minutes) : "-"}</td>
                    <td className="text-right">{batch.estimated_total_filament_grams || 0}g</td>
                    <td className="text-right">
                      <button
                        className="rounded-md border border-line bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={busyKey !== null}
                        onClick={() => exportBatch(batch)}
                        type="button"
                      >
                        {busyKey === `export-${batch.id}` ? "Export..." : "Export"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-md border border-line bg-slate-50 px-4 py-3 text-sm font-semibold text-muted">
            Nog geen batches. Gebruik het batchadvies hierboven om de eerste batch te maken.
          </div>
        )}
      </section>
    </div>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <input
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        inputMode="numeric"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}
