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
      {formatStatus(value)}
    </span>
  );
}
