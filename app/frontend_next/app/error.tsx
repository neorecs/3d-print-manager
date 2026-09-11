"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="mx-auto max-w-xl space-y-4 p-6" role="alert">
    <h1 className="text-xl font-bold">Gegevens konden niet worden geladen</h1>
    <p>De gegevens zijn niet beschikbaar. Probeer het opnieuw.</p>
    <button type="button" onClick={reset} className="rounded-md bg-brand px-4 py-2 font-bold text-slate-950">Opnieuw proberen</button>
    <a className="block text-brand" href="/">Naar dashboard</a>
  </main>;
}
