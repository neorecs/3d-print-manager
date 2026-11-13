type StatusBadgeProps = {
  status?: string | null;
};

const statusLabels: Record<string, string> = {
  klaar_voor_publicatie: "Klaar voor publicatie",
  synchronisatie_nodig: "Synchronisatie nodig",
  omgezet_naar_printtaak: "Printtaak aangemaakt",
  volledig_op_voorraad: "Volledig op voorraad",
  deels_op_voorraad: "Deels op voorraad",
  niet_op_voorraad: "Niet op voorraad",
  deels_te_printen: "Deels te printen",
  volledig_te_printen: "Volledig te printen",
  deels_mislukt: "Deels mislukt",
  niet_gepubliceerd: "Niet gepubliceerd",
  status_opgehaald: "Status bijgewerkt",
  aandacht_nodig: "Aandacht nodig",
};

export function formatStatus(status?: string | null) {
  const value = status || "onbekend";
  return statusLabels[value.toLowerCase()] || value.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
}

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.startsWith("niet ") || normalized.startsWith("niet_")) {
    return "bg-amber-50 text-amber-800 ring-amber-600/20";
  }
  if (["klaar", "gepubliceerd", "verwerkt", "afgerond", "online", "verbonden"].some((item) => normalized.includes(item))) {
    return "bg-emerald-50 text-emerald-700 ring-emerald-600/15";
  }
  if (["fout", "mislukt", "tekort", "offline"].some((item) => normalized.includes(item))) {
    return "bg-red-50 text-red-700 ring-red-600/15";
  }
  if (["nieuw", "nodig", "laag", "deels"].some((item) => normalized.includes(item))) {
    return "bg-amber-50 text-amber-800 ring-amber-600/20";
  }
  if (["gepland", "bezig", "sync"].some((item) => normalized.includes(item))) {
    return "bg-blue-50 text-blue-700 ring-blue-600/15";
  }
  return "bg-hover text-inkSoft ring-line";
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const value = status || "onbekend";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusTone(value)}`}>
      {formatStatus(value)}
    </span>
  );
}
