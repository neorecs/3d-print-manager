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
      />
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Connector modus"
            value={readiness.connectors_live_mode ? "Live" : "Mock"}
            note={readiness.live_calls_blocked ? "echte platformcalls geblokkeerd" : "echte platformcalls mogelijk"}
            tone={readiness.live_calls_blocked ? "good" : "warning"}
          />
          <MetricCard
            label="Platformkosten nu"
            value={readiness.platform_subscription_required_now ? "Nodig" : "Niet nodig"}
            note="voor voorbereiden en testen"
            tone={readiness.platform_subscription_required_now ? "warning" : "good"}
          />
          <MetricCard
            label="Secrets"
            value={readiness.credential_encryption_configured ? "Actief" : "Mist"}
            note="credential encryptie"
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
          description="Deze controles maken de applicatie klaar voor echte data, terwijl Etsy en Shopify nog in veilige mockmodus blijven."
        >
          <div className="grid gap-3">
            <CheckRow
              label="Live calls geblokkeerd"
              ok={readiness.live_calls_blocked}
              detail="CONNECTORS_LIVE_MODE moet false blijven totdat je bewust echte API-acties wilt uitvoeren."
            />
            <CheckRow
              label="Credential encryptie"
              ok={readiness.credential_encryption_configured}
              detail="Echte tokens worden alleen veilig opgeslagen met CREDENTIAL_ENCRYPTION_KEY."
            />
            <CheckRow
              label="Database ingesteld"
              ok={readiness.database_configured}
              detail="PostgreSQL is de bron voor producten, orders, voorraad, accounting en printerinstellingen."
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
              "AI concepten in mockmodus testen",
              "Voorraad en filament beheren",
              "Backups en herstel oefenen",
              "Bambu printers beheren",
              "Verkooplanden en talen voorbereiden",
              "Publicatievelden klaarzetten",
              "Connector credentials later pas toevoegen",
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
