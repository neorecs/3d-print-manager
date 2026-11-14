import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { ProductCreateForm } from "./ProductCreateForm";

export default function NewProductPage() {
  return (
    <AppShell>
      <PageHeader
        title="Nieuw product maken"
        description="Maak eerst een intern product aan. Daarna kun je foto's, platformpublicaties, voorraad en printplanning aanvullen."
        actions={
          <a className="rounded-md border border-line bg-surfaceSoft px-4 py-2 text-sm font-semibold text-inkSoft" href="/catalogus">
            Terug naar catalogus
          </a>
        }
      />
      <ProductCreateForm />
    </AppShell>
  );
}
