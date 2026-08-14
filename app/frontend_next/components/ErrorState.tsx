type ErrorStateProps = {
  title?: string;
  message?: string | null;
  retryHref?: string;
};

export function ErrorState({ title = "Gegevens konden niet worden geladen", message, retryHref = "" }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-red-400/25 bg-red-400/5 p-5">
      <h2 className="text-lg font-black text-ink">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">Ververs de pagina. Blijft dit gebeuren, controleer dan onder Instellingen of alle systeemcontroles gereed zijn.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <a className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950" href={retryHref || undefined}>Opnieuw proberen</a>
        <a className="rounded-md border border-line px-4 py-2 text-sm font-bold text-slate-200" href="/instellingen">Systeem controleren</a>
      </div>
      {message ? <details className="mt-4 text-xs text-muted"><summary className="cursor-pointer font-bold">Technische details voor ondersteuning</summary><pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-950/40 p-3">{message}</pre></details> : null}
    </div>
  );
}
