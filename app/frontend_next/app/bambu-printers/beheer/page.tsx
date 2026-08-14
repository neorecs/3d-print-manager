import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getBambuPrintersData } from "@/lib/api";
import { BambuPrinterManager } from "../BambuPrinterManager";

export const dynamic = "force-dynamic";

export default async function PrinterManagementPage() {
  const data = await getBambuPrintersData().catch(() => ({ printers: [] }));
  return (
    <AppShell>
      <PageHeader
        title="Printerbeheer"
        description="Technische printerinstellingen. Gebruik dit alleen om printers toe te voegen, verbindingen te testen of instellingen te wijzigen."
        actions={<a className="rounded-md border border-line px-4 py-2 text-sm font-bold text-slate-200 hover:border-brand" href="/bambu-printers">Terug naar printerstatus</a>}
      />
      <SectionCard title="Printers configureren" description="Access codes worden versleuteld opgeslagen en nooit opnieuw volledig getoond.">
        <BambuPrinterManager printers={data.printers} />
      </SectionCard>
    </AppShell>
  );
}
