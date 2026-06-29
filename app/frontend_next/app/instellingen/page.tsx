import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";

export default function SettingsPage() {
  return (
    <AppShell>
      <PageHeader
        title="Instellingen"
        description="Centrale plek voor systeemstatus, connectorinstellingen, secrets, backups en toekomstige voorkeuren."
      />
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Connector modus" value="Mock" note="live calls uit" tone="good" />
          <MetricCard label="Frontend" value="Next.js" note="officiele UI" />
          <MetricCard label="Streamlit" value="Fallback" note="nog beschikbaar" tone="warning" />
          <MetricCard label="Secrets" value="Extern" note="niet in Git" tone="good" />
        </div>

        <SectionCard title="Nog te koppelen instellingen" description="Deze pagina is de nieuwe bestemming voor instellingen die nu nog verspreid staan.">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {[
              "Etsy en Shopify credentials",
              "OpenAI kostenlimiet en mockmodus",
              "Backup- en herstelstatus",
              "Bambu printervoorkeuren",
              "Land- en taalinstellingen",
              "Administratie en btw-instellingen",
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
