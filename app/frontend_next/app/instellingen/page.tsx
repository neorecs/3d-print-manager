import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getSystemReadiness } from "@/lib/api";

export const dynamic = "force-dynamic";

type CheckState = "ready" | "attention" | "deferred";

function CheckRow({ label, state, detail }: { label: string; state: CheckState; detail: string }) {
  const status = state === "ready" ? "klaar" : state === "deferred" ? "uitgesteld" : "aandacht_nodig";
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line bg-panelSoft p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="text-sm font-black text-ink">{label}</div>
        <div className="mt-1 text-sm text-muted">{detail}</div>
      </div>
      <StatusBadge status={status} />
    </div>
  );
}

function evidenceDate(value?: string | null) {
  if (!value) return "Geen geslaagde controle geregistreerd";
  return `Laatste bewijs: ${new Intl.DateTimeFormat("nl-NL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))}`;
}

function BlockerList({ blockers, success }: { blockers: string[]; success: string }) {
  if (!blockers.length) return <div className="rounded-xl border border-emerald-400/25 bg-emerald-950/20 p-4 text-sm font-bold text-emerald-100">{success}</div>;
  return <div className="space-y-3">{blockers.map((blocker) => <div className="rounded-xl border border-amber-400/25 bg-amber-950/20 p-4 text-sm font-bold text-amber-100" key={blocker}>{blocker}</div>)}</div>;
}

export default async function SettingsPage() {
  const readiness = await getSystemReadiness();

  return (
    <AppShell>
      <PageHeader
        title="Instellingen"
        description="Bekijk apart wat klaar is voor intern gebruik, verkoopkanalen en latere internettoegang."
        actions={<div className="flex flex-wrap gap-2"><a className="rounded-md border border-line px-3 py-2 text-sm font-bold" href="/account/beveiliging">Account</a><a className="rounded-md border border-line px-3 py-2 text-sm font-bold" href="/instellingen/gebruikers">Gebruikers</a></div>}
      />
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Intern gebruik"
            value={readiness.internal_use_ready ? "Klaar" : "Aandacht"}
            note="producten, voorraad en planning"
            tone={readiness.internal_use_ready ? "good" : "warning"}
          />
          <MetricCard
            label="Verkoopkanalen"
            value={readiness.connectors_live_mode ? "Live actief" : "Veilige teststand"}
            note={readiness.live_calls_blocked ? "geen live platformwijzigingen" : "echte koppelingen ingeschakeld"}
            tone={readiness.live_calls_blocked ? "good" : "warning"}
          />
          <MetricCard
            label="Platformtokens"
            value={readiness.ready_for_real_tokens ? "Opslag klaar" : "Nog niet veilig"}
            note="versleuteling, backups en herstelbewijs"
            tone={readiness.ready_for_real_tokens ? "good" : "danger"}
          />
          <MetricCard
            label="Internettoegang"
            value={readiness.external_access_ready ? "Techniek klaar" : "Uitgesteld"}
            note={readiness.external_access_ready ? "secure cookies actief" : "pas bij domein en HTTPS"}
            tone={readiness.external_access_ready ? "good" : "neutral"}
          />
        </div>

        <SectionCard
          title="1. Intern gebruiken"
          description="Voor echte producten, voorraad, planning en administratie op het vertrouwde lokale netwerk. Platformtokens zijn hiervoor niet nodig."
        >
          <div className="grid gap-3">
            <CheckRow
              label="Gebruikerslogin en interne toegang"
              state={readiness.auth_enabled && readiness.auth_backend_login && readiness.internal_api_configured && readiness.session_signing_configured ? "ready" : "attention"}
              detail="De interface gebruikt databaseaccounts en interne aanvragen zijn afgeschermd."
            />
            <CheckRow
              label="Database bereikbaar"
              state={readiness.database_reachable ? "ready" : "attention"}
              detail="De PostgreSQL-database is bereikbaar vanuit de app."
            />
            <CheckRow
              label="Bestandsopslag"
              state={readiness.upload_storage_writable ? "ready" : "attention"}
              detail="Foto's, documenten en printbestanden moeten op de permanente opslag geschreven kunnen worden."
            />
            <CheckRow
              label="Databasebackup"
              state={readiness.database_backup_recent ? "ready" : "attention"}
              detail={`${evidenceDate(readiness.database_backup_last_success)}. Maximaal 48 uur oud.`}
            />
            <CheckRow
              label="Bestandsbackup"
              state={readiness.upload_backup_configured && readiness.upload_backup_recent ? "ready" : "attention"}
              detail={`${evidenceDate(readiness.upload_backup_last_success)}. Maximaal 48 uur oud.`}
            />
            <CheckRow
              label="Gezamenlijke hersteltest"
              state={readiness.restore_test_recent ? "ready" : "attention"}
              detail={`${evidenceDate(readiness.restore_test_last_success)}. Database en bestanden moeten samen zijn hersteld; maximaal 90 dagen oud.`}
            />
            <CheckRow
              label="Backupplan aanwezig"
              state={readiness.backup_plan_documented ? "ready" : "attention"}
              detail="De praktische backup- en herstelstappen staan in de documentatie."
            />
          </div>
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-3">
          <SectionCard title="Blokkades intern gebruik" description="Alleen punten die echte lokale bedrijfsgegevens onveilig of onbetrouwbaar maken.">
            <BlockerList blockers={readiness.internal_blockers} success="Geen technische blokkades voor intern gebruik. Controleer de praktijkworkflow nog via de acceptatiechecklist." />
          </SectionCard>

          <SectionCard title="2. Echte platformtokens" description="HTTPS is hiervoor geen blokkade zolang je de site uitsluitend via het vertrouwde lokale netwerk gebruikt.">
            <CheckRow label="Versleutelde opslag" state={readiness.credential_encryption_configured ? "ready" : "attention"} detail="Platformtokens worden versleuteld in de database opgeslagen." />
            <div className="mt-3"><CheckRow label="Veilige teststand" state={readiness.live_calls_blocked ? "ready" : "attention"} detail="Live platformacties blijven uit totdat je bewust één kanaal test." /></div>
            <div className="mt-3"><BlockerList blockers={readiness.platform_blockers} success="De opslag en herstelbasis voor echte tokens is klaar. Voeg tokens alleen via de app toe." /></div>
          </SectionCard>

          <SectionCard title="3. Toegang via internet" description="Dit staat los van uitgaande Etsy- of Shopify-koppelingen en is bewust uitgesteld tot je een domein gebruikt.">
            <CheckRow label="Domein, HTTPS en secure cookies" state={readiness.external_access_ready ? "ready" : "deferred"} detail={readiness.external_access_ready ? "De technische cookie-instelling voor HTTPS is actief; controleer ook het certificaat en de publieke route." : "Niet nodig voor lokaal gebruik. Maak de site nog niet buiten het lokale netwerk bereikbaar."} />
            <div className="mt-3"><BlockerList blockers={readiness.external_access_blockers} success="Geen gemelde technische blokkade; verifieer domein, certificaat en externe route apart." /></div>
          </SectionCard>

          <SectionCard title="Volgende controles" description="Praktische volgorde vanaf de huidige situatie.">
            <div className="space-y-3">
              {readiness.next_checks.map((check) => (
                <div className="rounded-xl border border-line bg-panelSoft p-4 text-sm font-semibold text-slate-200" key={check}>
                  {check}
                </div>
              ))}
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Wat kan zonder Etsy of Shopify abonnement?" description="Deze voorbereidingen staan los van internettoegang en betaalde verkoopplatformafspraken.">
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
