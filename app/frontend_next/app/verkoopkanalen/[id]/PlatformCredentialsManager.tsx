"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Platform, PlatformConnectorStatus, PlatformCredential } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

type Props = {
  platform: Platform;
  status: PlatformConnectorStatus | null;
  credentials: PlatformCredential[];
};

export function PlatformCredentialsManager({ platform, status, credentials }: Props) {
  const router = useRouter();
  const suggestedKeys = useMemo(() => {
    const keys = [...(status?.missing_credentials || []), ...(status?.required_credentials || []), ...credentials.map((item) => item.key_name)];
    return Array.from(new Set(keys)).filter(Boolean);
  }, [credentials, status]);
  const [keyName, setKeyName] = useState(suggestedKeys[0] || "");
  const [secretValue, setSecretValue] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function saveCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("save");
    setMessage(null);
    setError(null);
    try {
      if (!keyName.trim()) throw new Error("Vul een credentialnaam in.");
      if (!secretValue.trim()) throw new Error("Vul de token/waarde in.");
      const response = await fetch(`/api/platforms/${platform.id}/credentials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key_name: keyName.trim(), encrypted_value: secretValue }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Credential kon niet worden opgeslagen");
      setSecretValue("");
      setMessage("Credential opgeslagen. De waarde wordt hierna niet meer getoond.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function deleteCredential(id: number) {
    setBusyKey(`delete-${id}`);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/platform-credentials/${id}`, { method: "DELETE" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Credential kon niet worden verwijderd");
      setMessage("Credential verwijderd.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verwijderen is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-5">
      {message ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div> : null}

      <form className="rounded-lg border border-line bg-slate-950/25 p-4" onSubmit={saveCredential}>
        <div className="grid gap-4 md:grid-cols-[minmax(180px,280px)_1fr_auto] md:items-end">
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Credentialnaam</span>
            <input
              className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand"
              list="credential-key-suggestions"
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="Bijv. access_token"
              value={keyName}
            />
            <datalist id="credential-key-suggestions">
              {suggestedKeys.map((key) => <option key={key} value={key} />)}
            </datalist>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Token of geheime waarde</span>
            <input
              className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-ink text-sm outline-none focus:border-brand"
              onChange={(event) => setSecretValue(event.target.value)}
              placeholder="Wordt versleuteld opgeslagen en niet teruggetoond"
              type="password"
              value={secretValue}
            />
          </label>
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busyKey === "save"} type="submit">
            {busyKey === "save" ? "Opslaan..." : "Opslaan"}
          </button>
        </div>
        <p className="mt-3 text-sm text-muted">
          Gebruik alleen echte Etsy/Shopify tokens wanneer je zeker weet dat dit kanaal live gekoppeld mag worden.
        </p>
      </form>

      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Credential</th><th>Status</th><th>Opslag</th><th>Actie</th></tr></thead>
          <tbody>
            {credentials.length ? credentials.map((credential) => (
              <tr key={credential.id}>
                <td className="font-semibold">{credential.key_name}</td>
                <td><StatusBadge status={credential.has_value ? "ingevuld" : "leeg"} /></td>
                <td>{credential.encrypted ? "versleuteld" : "onbekend"}</td>
                <td>
                  <button
                    className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
                    disabled={busyKey === `delete-${credential.id}`}
                    onClick={() => deleteCredential(credential.id)}
                    type="button"
                  >
                    {busyKey === `delete-${credential.id}` ? "Verwijderen..." : "Verwijderen"}
                  </button>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={4}>Nog geen credentials opgeslagen.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

