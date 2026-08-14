import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { getAIProductStatus } from "@/lib/api";
import type { AIProductStatus } from "@/lib/types";
import { AIProductAssistant } from "./AIProductAssistant";

export default async function AIProductAssistantPage() {
  let status: AIProductStatus | null = null;
  let error: string | null = null;
  try {
    status = await getAIProductStatus();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="AI Product Assistent"
        description="Maak productconcepten voor titel, omschrijving, tags, SEO en varianten. De gratis teststand gebruikt geen betaalde AI-aanvragen."
        actions={<a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300" href="/catalogus">Naar catalogus</a>}
      />
      <SectionCard title="Productconcept maken" description="Controleer altijd zelf de output voordat je iets opslaat of publiceert.">
        {error || !status ? <ErrorState message={error} retryHref="/catalogus/ai-assistent" title="AI-assistent kon niet worden geladen" /> : <AIProductAssistant status={status} />}
      </SectionCard>
    </AppShell>
  );
}
