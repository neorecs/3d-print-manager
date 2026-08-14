import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getSystemReadiness } from "@/lib/api";

export const dynamic = "force-dynamic";

function CheckRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line bg-panelSoft p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="text-sm font-black text-ink">{label}</div>
        <div className="mt-1 text-sm text-muted">{detail}</div>
      </div>
      <StatusBadge status={ok ? "klaar" : "aandacht nodig"} />
    </div>
  );
}

export default async function SettingsPage() {
  const readiness = await getSystemReadiness();

  return (
    <AppShell>
      <PageHeader
        title="Instellingen"
        description="Live-klaar maken zonder nu al betaalde Etsy- of Shopify-afspraken te sluiten."
        actions={<div className="flex flex-wrap gap-2"><a className="rounded-md border border-line px-3 py-2 text-sm font-bold" href="/account/beveiliging">Account</a><a className="rounded-md border border-line px-3 py-2 text-sm font-bold" href="/instellingen/gebruikers">Gebruikers</a></div>}
      />
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Koppelingsstand"
            value={readiness.connectors_live_mode ? "Live" : "Veilige teststand"}
            note={readiness.live_calls_blocked ? "geen wijzigingen naar verkoopkanalen" : "live verbinding actief"}
            tone={readiness.live_calls_blocked ? "good" : "warning"}
          />
          <MetricCard
            label="Platformkosten nu"
            value={readiness.platform_subscription_required_now ? "Nodig" : "Niet nodig"}
            note="voor voorbereiden en testen"
            tone={readiness.platform_subscription_required_now ? "warning" : "good"}
          />
          <MetricCard
            label="Versleuteling"
            value={readiness.credential_encryption_configured ? "Actief" : "Mist"}
            note="toegangsgegevens beschermd"
            tone={readiness.credential_encryption_configured ? "good" : "danger"}
          />
          <MetricCard
            label="Echte tokens"
            value={readiness.ready_for_real_tokens ? "Voorbereid" : "Nog niet"}
            note="opslaan kan pas veilig met encryptie"
            tone={readiness.ready_for_real_tokens ? "good" : "warning"}
          />
        </div>

        <SectionCard
          title="Live-klaar zonder abonnement"
          description="Deze controles maken de applicatie klaar voor echte gegevens, terwijl Etsy en Shopify nog in de veilige teststand blijven."
        >
          <div className="grid gap-3">
            <CheckRow
              label="Live platformcontact geblokkeerd"
              ok={readiness.live_calls_blocked}
              detail="De app kan in de teststand geen echte wijzigingen naar Etsy of Shopify sturen."
            />
            <CheckRow
              label="Toegangsgegevens versleuteld"
              ok={readiness.credential_encryption_configured}
              detail="Geheime sleutels en tokens worden alleen versleuteld opgeslagen."
            />
            <CheckRow
              label="Interne diensten afgeschermd"
              ok={readiness.internal_api_configured && readiness.session_signing_configured}
              detail="Alle interne aanvragen vereisen een geldige gebruikerssessie en beveiligde interne toegang."
            />
            <CheckRow
              label="Gegevensopslag bereikbaar"
              ok={readiness.database_reachable}
              detail="De centrale gegevensopslag is bereikbaar en gecontroleerd."
            />
            <CheckRow
              label="Bestandsopslag"
              ok={readiness.upload_storage_writable}
              detail="Foto's, documenten en printbestanden moeten op de permanente opslag geschreven kunnen worden."
            />
            <CheckRow
              label="Databasebackup recent"
              ok={readiness.database_backup_recent}
              detail="De laatste geslaagde PostgreSQL-backup mag maximaal 48 uur oud zijn."
            />
            <CheckRow
              label="Bestandsbackup recent"
              ok={readiness.upload_backup_configured && readiness.upload_backup_recent}
              detail="De laatste backup van foto's, documenten en printbestanden mag maximaal 48 uur oud zijn."
            />
            <CheckRow
              label="Hersteltest recent"
              ok={readiness.restore_test_recent}
              detail="Database en uploads zijn in de afgelopen 90 dagen gezamenlijk teruggezet en gecontroleerd."
            />
            <CheckRow
              label="Database-login"
              ok={readiness.auth_enabled && readiness.auth_backend_login}
              detail="De hoofdinterface gebruikt ingeschakelde databaseaccounts voor toegang."
            />
            <CheckRow
              label="Externe toegang"
              ok={!readiness.connectors_live_mode || readiness.secure_cookie_enabled}
              detail={readiness.secure_cookie_enabled ? "Beveiligde externe toegang is actief." : "Uitgesteld zolang de app alleen op het lokale netwerk wordt gebruikt."}
            />
            <CheckRow
              label="Backupplan aanwezig"
              ok={readiness.backup_plan_documented}
              detail="De praktische backup- en herstelstappen staan in de documentatie."
            />
          </div>
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="Nog blokkades" description="Dit moet opgelost zijn voordat je echte platformtokens bewaart of live calls toestaat.">
            {readiness.blockers.length ? (
              <div className="space-y-3">
                {readiness.blockers.map((blocker) => (
                  <div className="rounded-xl border border-amber-400/25 bg-amber-950/20 p-4 text-sm font-bold text-amber-100" key={blocker}>
                    {blocker}
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-emerald-400/25 bg-emerald-950/20 p-4 text-sm font-bold text-emerald-100">
                Geen technische blokkades voor veilig voorbereiden. Laat live modus nog uit totdat je echte platformtests plant.
              </div>
            )}
          </SectionCard>

          <SectionCard title="Volgende controles" description="Praktische checklist voordat de app echte orders of tokens krijgt.">
            <div className="space-y-3">
              {readiness.next_checks.map((check) => (
                <div className="rounded-xl border border-line bg-panelSoft p-4 text-sm font-semibold text-slate-200" key={check}>
                  {check}
                </div>
              ))}
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Wat kan zonder Etsy of Shopify abonnement?" description="Je kunt bijna alles voorbereiden zonder nu kosten bij verkoopplatformen te maken.">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              "Productcatalogus vullen",
              "AI-concepten in gratis teststand maken",
              "Voorraad en filament beheren",
              "Backups en herstel oefenen",
              "Bambu printers beheren",
              "Verkooplanden en talen voorbereiden",
              "Publicatievelden klaarzetten",
              "Toegang tot verkoopkanalen later toevoegen",
            ].map((item) => (
              <div className="rounded-xl border border-line bg-panelSoft p-4 text-sm font-bold text-slate-200" key={item}>
                {item}
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}
