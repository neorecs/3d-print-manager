"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import type { Platform, PlatformConnectorStatus, PlatformCredential } from "@/lib/types";

type Props = {
  platform: Platform;
  status: PlatformConnectorStatus | null;
  credentials: PlatformCredential[];
};

type CredentialField = {
  key: string;
  label: string;
  description: string;
  placeholder: string;
  secret?: boolean;
  optional?: boolean;
};

const platformFields: Record<string, CredentialField[]> = {
  etsy: [
    { key: "api_key", label: "API-key", description: "De Etsy App API Key keystring uit het Developer Portal.", placeholder: "Plak hier de Etsy API-key", secret: true },
    { key: "shared_secret", label: "App-geheim", description: "Het Shared Secret dat bij de Etsy API-key hoort.", placeholder: "Plak hier het Etsy Shared Secret", secret: true },
    { key: "access_token", label: "OAuth-toegangstoken", description: "Geeft toegang tot jouw Etsy-winkel. Dit wordt later via Verbinden met Etsy opgehaald.", placeholder: "Plak hier voorlopig het OAuth-token", secret: true },
    { key: "shop_id", label: "Winkelnummer", description: "Het numerieke shop-ID van jouw Etsy-winkel.", placeholder: "Bijvoorbeeld 12345678" },
    { key: "taxonomy_id", label: "Standaardcategorie", description: "Etsy categorie-ID voor nieuwe publicaties.", placeholder: "Numerieke Etsy categorie-ID" },
    { key: "readiness_state_id", label: "Verwerkingsprofiel", description: "Etsy processing profile voor fysieke producten.", placeholder: "Numeriek verwerkingsprofiel-ID" },
    { key: "variation_property_id", label: "Variatie-eigenschap", description: "Alleen nodig als Etsy-varianten een taxonomy property gebruiken.", placeholder: "Numerieke property-ID", optional: true },
  ],
  shopify: [
    { key: "shop_domain", label: "Winkeladres", description: "Het permanente myshopify.com-adres van de winkel.", placeholder: "jouw-winkel.myshopify.com" },
    { key: "access_token", label: "Admin API-token", description: "Het Shopify Admin API access token.", placeholder: "Plak hier het Admin API-token", secret: true },
    { key: "location_id", label: "Voorraadlocatie", description: "Shopify location-ID voor voorraadsynchronisatie.", placeholder: "Numeriek location-ID", optional: true },
  ],
};

export function PlatformCredentialsManager({ platform, status, credentials }: Props) {
  const router = useRouter();
  const fields = useMemo(() => {
    const known = platformFields[platform.type.toLowerCase()] || [];
    const knownKeys = new Set(known.map((field) => field.key));
    const additionalKeys = [
      ...(status?.required_credentials || []),
      ...(status?.missing_credentials || []),
      ...credentials.map((item) => item.key_name),
    ].filter((key) => key && !knownKeys.has(key));
    const additional: CredentialField[] = Array.from(new Set(additionalKeys)).map((key) => ({
      key,
      label: key,
      description: "Aanvullend gegeven dat deze connector gebruikt.",
      placeholder: "Vul de waarde in",
      secret: true,
    }));
    return [...known, ...additional];
  }, [credentials, platform.type, status]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function credentialFor(key: string) {
    return credentials.find((credential) => credential.key_name === key);
  }

  async function saveCredential(event: FormEvent<HTMLFormElement>, field: CredentialField) {
    event.preventDefault();
    const value = values[field.key]?.trim() || "";
    setBusyKey(field.key);
    setMessage(null);
    setError(null);
    try {
      if (!value) throw new Error(`Vul ${field.label.toLowerCase()} in.`);
      const response = await fetch(`/api/platforms/${platform.id}/credentials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key_name: field.key, encrypted_value: value }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || `${field.label} kon niet worden opgeslagen`);
      setValues((current) => ({ ...current, [field.key]: "" }));
      setMessage(`${field.label} is versleuteld opgeslagen.`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Opslaan is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  async function deleteCredential(credential: PlatformCredential, label: string) {
    setBusyKey(`delete-${credential.id}`);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`/api/platform-credentials/${credential.id}`, { method: "DELETE" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || `${label} kon niet worden verwijderd`);
      setMessage(`${label} is verwijderd.`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verwijderen is mislukt");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-4">
      {message ? <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</div> : null}

      <div className="space-y-3">
        {fields.map((field) => {
          const credential = credentialFor(field.key);
          const busy = busyKey === field.key || busyKey === `delete-${credential?.id}`;
          return (
            <form className="rounded-md border border-line bg-slate-950/25 p-4" key={field.key} onSubmit={(event) => saveCredential(event, field)}>
              <div className="grid gap-4 xl:grid-cols-[minmax(220px,1fr)_minmax(260px,1.3fr)_auto] xl:items-end">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-black text-ink">{field.label}</span>
                    {field.optional ? <span className="text-xs font-bold text-muted">optioneel</span> : null}
                    <StatusBadge status={credential?.has_value ? "ingevuld" : "ontbreekt"} />
                  </div>
                  <p className="mt-2 text-sm text-muted">{field.description}</p>
                </div>
                <label className="space-y-2">
                  <span className="text-sm font-bold text-slate-300">{credential?.has_value ? "Nieuwe waarde om te vervangen" : field.label}</span>
                  <input
                    autoComplete="off"
                    className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand"
                    onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
                    placeholder={credential?.has_value ? "Huidige waarde blijft verborgen" : field.placeholder}
                    type={field.secret ? "password" : "text"}
                    value={values[field.key] || ""}
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button className="rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-60" disabled={busy} type="submit">
                    {busyKey === field.key ? "Opslaan..." : credential?.has_value ? "Vervangen" : "Opslaan"}
                  </button>
                  {credential ? (
                    <button className="rounded-md border border-red-400/25 px-3 py-2 text-sm font-bold text-red-300 hover:bg-red-400/10 disabled:opacity-60" disabled={busy} onClick={() => deleteCredential(credential, field.label)} type="button">
                      {busyKey === `delete-${credential.id}` ? "Verwijderen..." : "Verwijderen"}
                    </button>
                  ) : null}
                </div>
              </div>
            </form>
          );
        })}
      </div>

      <p className="text-sm text-muted">Opgeslagen geheime waarden worden nooit teruggetoond. Lege velden vervangen bestaande waarden niet.</p>
    </div>
  );
}
