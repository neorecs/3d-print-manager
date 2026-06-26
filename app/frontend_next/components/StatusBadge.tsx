type StatusBadgeProps = {
  status?: string | null;
};

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (["klaar", "gepubliceerd", "verwerkt", "afgerond", "online"].some((item) => normalized.includes(item))) {
    return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  }
  if (["fout", "mislukt", "tekort", "offline"].some((item) => normalized.includes(item))) {
    return "bg-red-50 text-red-700 ring-red-200";
  }
  if (["nieuw", "nodig", "laag", "deels"].some((item) => normalized.includes(item))) {
    return "bg-amber-50 text-amber-700 ring-amber-200";
  }
  if (["gepland", "bezig", "sync"].some((item) => normalized.includes(item))) {
    return "bg-blue-50 text-blue-700 ring-blue-200";
  }
  return "bg-slate-50 text-slate-700 ring-slate-200";
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const value = status || "onbekend";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${statusTone(value)}`}>
      {value.replace(/_/g, " ")}
    </span>
  );
}
