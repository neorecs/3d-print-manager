import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Card } from "@/components/ui";
import { formatCurrency, getListingPackage, type ListingPackage } from "@/lib/api";
import { CopyField } from "./CopyField";
import { MarkPlacedForm } from "./MarkPlacedForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "Plaatsingspakket" };

export default async function ListingPackagePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const publicationId = Number(id);
  if (!Number.isInteger(publicationId) || publicationId < 1) notFound();
  let data: ListingPackage | null = null;
  let error: string | null = null;
  try {
    data = await getListingPackage(publicationId);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Plaatsingspakket niet beschikbaar";
  }

  return (
    <AppShell>
      {error || !data ? (
        <ErrorState message={error || "Geen gegevens"} title="Plaatsingspakket niet beschikbaar" />
      ) : (
        <>
          <PageHeader
            actions={<StatusBadge status={data.placed_manually ? "geplaatst" : "nog niet geplaatst"} />}
            description="Kopieer elk veld naar het formulier van het kanaal, upload de foto's en markeer de advertentie daarna als geplaatst."
            title={`Plaatsen op ${data.platform.name}`}
          />
          <div className="space-y-6">
            {data.validation.errors.length || data.profile.notes.length ? (
              <Card className="space-y-2 px-5 py-4">
                {data.validation.errors.map((message) => <p className="text-sm font-medium text-red-700" key={message}>{message}</p>)}
                {data.profile.notes.map((note) => <p className="text-sm text-muted" key={note}>{note}</p>)}
              </Card>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-2">
              <CopyField label="Titel" limit={data.profile.title_max} value={data.title} />
              <CopyField label="Prijs" value={data.price != null ? formatCurrency(data.price).replace(/ /g, " ") : ""} />
              <div className="lg:col-span-2"><CopyField label="Omschrijving" multiline value={data.description} /></div>
              {data.tags.length ? <CopyField label="Zoekwoorden" value={data.tags.join(", ")} /> : null}
              {data.category ? <CopyField label="Categorie" value={data.category} /> : null}
            </div>
            <Card className="px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-ink">Foto&apos;s ({data.photos.length}{data.profile.photos_max ? ` van max. ${data.profile.photos_max}` : ""})</h2>
                {data.photos.length ? <a className="min-h-10 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-inkSoft hover:bg-hover" href={`/api/product-publications/${data.publication_id}/photos`}>Alle foto&apos;s downloaden</a> : null}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
                {data.photos.map((photo, index) => (
                  <figure className="space-y-1" key={photo.id}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img alt={photo.alt_text || `Foto ${index + 1}`} className="aspect-square w-full rounded-lg border border-line object-cover" src={photo.url} />
                    <figcaption className="text-xs text-muted">{index + 1}. {photo.ai_edited ? "AI-bewerkt" : "Origineel"}</figcaption>
                  </figure>
                ))}
              </div>
            </Card>
            {data.variants.length > 1 ? (
              <Card className="px-5 py-4">
                <h2 className="text-base font-semibold text-ink">Varianten</h2>
                <ul className="mt-3 space-y-1 text-sm text-ink">
                  {data.variants.map((variant) => (
                    <li key={variant.sku}>{variant.name} · {[variant.color, variant.material].filter(Boolean).join(", ")} · {variant.price != null ? formatCurrency(variant.price) : "-"}</li>
                  ))}
                </ul>
              </Card>
            ) : null}
            <Card className="px-5 py-4">
              <MarkPlacedForm externalUrl={data.external_url} placed={data.placed_manually} publicationId={data.publication_id} />
            </Card>
          </div>
        </>
      )}
    </AppShell>
  );
}
