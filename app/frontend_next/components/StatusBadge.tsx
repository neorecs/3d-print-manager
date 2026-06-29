type StatusBadgeProps = {
  status?: string | null;
};

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (["klaar", "gepubliceerd", "verwerkt", "afgerond", "online"].some((item) => normalized.includes(item))) {
    return "bg-emerald-400/10 text-emerald-300 ring-emerald-400/25";
  }
  if (["fout", "mislukt", "tekort", "offline"].some((item) => normalized.includes(item))) {
    return "bg-red-400/10 text-red-300 ring-red-400/25";
  }
  if (["nieuw", "nodig", "laag", "deels"].some((item) => normalized.includes(item))) {
    return "bg-amber-400/10 text-amber-200 ring-amber-400/25";
  }
  if (["gepland", "bezig", "sync"].some((item) => normalized.includes(item))) {
    return "bg-blue-400/10 text-blue-300 ring-blue-400/25";
  }
  return "bg-slate-400/10 text-slate-300 ring-slate-400/25";
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const value = status || "onbekend";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${statusTone(value)}`}>
      {value.replace(/_/g, " ")}
    </span>
  );
}
