"use client";

import { useState } from "react";

export function CopyField({ label, value, multiline = false, limit }: { label: string; value: string; multiline?: boolean; limit?: number | null }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  const over = limit ? value.length > limit : false;
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-ink">{label}</span>
        <div className="flex items-center gap-3">
          {limit ? <span className={`text-xs tabular-nums ${over ? "font-semibold text-red-700" : "text-muted"}`}>{value.length} / {limit}</span> : null}
          <button className="rounded-lg border border-line px-3 py-1.5 text-sm font-semibold text-inkSoft hover:bg-hover" onClick={copy} type="button">
            {copied ? "Gekopieerd" : "Kopiëren"}
          </button>
        </div>
      </div>
      <div className={`mt-2 text-sm text-ink ${multiline ? "whitespace-pre-wrap" : "break-words"}`}>{value || <span className="text-muted">Leeg</span>}</div>
    </div>
  );
}
