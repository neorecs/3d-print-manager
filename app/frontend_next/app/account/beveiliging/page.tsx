import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { SecuritySettings } from "./SecuritySettings";

export default function AccountSecurityPage() {
  return (
    <AppShell>
      <PageHeader
        title="Accountbeveiliging"
        description="Beheer je eigen loginbeveiliging. Zet MFA aan voordat de app buiten je lokale netwerk beschikbaar wordt."
      />
      <div className="space-y-6">
        <SectionCard
          title="Wat doe ik hier?"
          description="Koppel een authenticator-app aan je account. Daarna heb je naast je wachtwoord ook een 6-cijferige code nodig."
        >
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-line bg-panelSoft p-4">
              <div className="text-sm font-black text-white">1. Setup starten</div>
              <div className="mt-2 text-sm text-muted">Vul je huidige wachtwoord in.</div>
            </div>
            <div className="rounded-xl border border-line bg-panelSoft p-4">
              <div className="text-sm font-black text-white">2. Code toevoegen</div>
              <div className="mt-2 text-sm text-muted">Zet de setup-code in je authenticator-app.</div>
            </div>
            <div className="rounded-xl border border-line bg-panelSoft p-4">
              <div className="text-sm font-black text-white">3. Bevestigen</div>
              <div className="mt-2 text-sm text-muted">Vul de 6-cijferige code in om MFA te activeren.</div>
            </div>
          </div>
        </SectionCard>
        <SecuritySettings />
      </div>
    </AppShell>
  );
}
