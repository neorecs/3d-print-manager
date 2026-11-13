import type { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string | null };

/** Labelled text field with optional hint or error message. */
export function Input({ label, hint, error, className = "", id, ...props }: InputProps) {
  const fieldId = id || `veld-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <label className="flex flex-col gap-1.5 text-sm font-medium text-ink" htmlFor={fieldId}>
      {label}
      <input
        aria-invalid={error ? true : undefined}
        className={`min-h-10 rounded-lg border bg-panel px-3 text-sm font-normal text-ink outline-none focus:border-brand ${error ? "border-red-700" : "border-line"} ${className}`.trim()}
        id={fieldId}
        {...props}
      />
      {error ? <span className="text-xs font-medium text-red-700">{error}</span> : hint ? <span className="text-xs font-normal text-muted">{hint}</span> : null}
    </label>
  );
}
