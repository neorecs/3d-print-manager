"use client";

import { FormEvent, useEffect, useState } from "react";

export type PrinterBridge = {
  id: number;
  name: string;
  token_hint: string;
  agent_version?: string | null;
  last_seen_at?: string | null;
  online: boolean;
  revoked: boolean;
  printers: { id: number; name: string }[];
};

export function BridgeManager({ bridges, onChange }: { bridges: PrinterBridge[]; onChange: () => void }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ name: string; token: string } | null>(null);
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/bridges", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Bridge aanmaken mislukt.");
      setCreated({ name: data.name, token: data.token });
      setName("");
      onChange();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Bridge aanmaken mislukt.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(bridge: PrinterBridge) {
    if (!window.confirm(`Bridge '${bridge.name}' intrekken? De agent op die locatie kan daarna niet meer verbinden.`)) return;
    await fetch(`/api/bridges/${bridge.id}/revoke`, { method: "POST" });
    onChange();
  }

  const command = created
    ? `BRIDGE_APP_URL=${origin} BRIDGE_TOKEN=${created.token} docker compose up -d --build`
    : "";

  return (
    <section className="rounded-lg border border-line bg-surfaceSoft p-4">
      <h3 className="font-semibold text-ink">Printers op een andere locatie (bridge)</h3>
      <p className="mt-1 text-sm text-muted">
        Bambu-printers buiten je eigen netwerk bedien je via een bridge: een klein programma op een computer, NAS of Raspberry Pi in het netwerk van die printers.
        De bridge maakt zelf een beveiligde verbinding met deze app, dus daar hoeft niets opengezet te worden. Daarna kies je bij de printer de verbinding &quot;Via bridge&quot;.
      </p>

      {bridges.length ? (
        <ul className="mt-4 divide-y divide-line rounded-md border border-line bg-panel">
          {bridges.map((bridge) => (
            <li className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-sm" key={bridge.id}>
              <div>
                <span className="font-semibold text-ink">{bridge.name}</span>
                <span className="ml-2 text-muted">token {bridge.token_hint}</span>
                <div className="text-xs text-muted">
                  {bridge.printers.length ? bridge.printers.map((printer) => printer.name).join(", ") : "nog geen printers"}
                  {bridge.last_seen_at ? ` · laatst gezien ${new Date(bridge.last_seen_at).toLocaleString("nl-NL")}` : " · nog nooit verbonden"}
                  {bridge.agent_version ? ` · versie ${bridge.agent_version}` : ""}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${bridge.revoked ? "bg-track text-muted ring-line" : bridge.online ? "bg-emerald-400/10 text-emerald-700 ring-emerald-200" : "bg-amber-400/10 text-amber-800 ring-amber-200"}`}>
                  {bridge.revoked ? "ingetrokken" : bridge.online ? "online" : "offline"}
                </span>
                {!bridge.revoked ? <button className="text-xs font-semibold text-red-700" onClick={() => revoke(bridge)} type="button">Intrekken</button> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {created ? (
        <div className="mt-4 rounded-md border border-brand bg-brandSoft p-3 text-sm text-ink">
          <p className="font-semibold">Bridge &apos;{created.name}&apos; aangemaakt. Deze token zie je maar één keer.</p>
          <p className="mt-1 text-inkSoft">Zet de map <code>ops/bambu-bridge</code> uit de repository op een computer in het netwerk van de printers en start daar (Docker):</p>
          <pre className="mt-2 overflow-x-auto rounded-md border border-line bg-panel p-3 text-xs">{command}</pre>
          <p className="mt-2 text-xs text-muted">Uitleg en een variant zonder Docker staan in ops/bambu-bridge/README.md. Dit adres moet via HTTPS vanaf die locatie bereikbaar zijn.</p>
          <button className="mt-2 rounded-md border border-line bg-panel px-3 py-1.5 text-xs font-semibold" onClick={() => navigator.clipboard?.writeText(command)} type="button">Kopiëren</button>
        </div>
      ) : null}

      <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={create}>
        <label className="min-w-56 flex-1 space-y-1">
          <span className="text-sm font-semibold text-inkSoft">Nieuwe bridge</span>
          <input className="w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink outline-none focus:border-brand" onChange={(event) => setName(event.target.value)} placeholder="Bijv. Werkplaats ouders" required value={name} />
        </label>
        <button className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-onBrand disabled:opacity-60" disabled={busy} type="submit">{busy ? "Aanmaken..." : "Bridge aanmaken"}</button>
        {error ? <span className="text-sm font-semibold text-red-700">{error}</span> : null}
      </form>
    </section>
  );
}
