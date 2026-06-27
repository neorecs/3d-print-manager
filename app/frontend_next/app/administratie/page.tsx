import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, getAccountingData } from "@/lib/api";
import type { AccountingData } from "@/lib/types";
import { AccountingPurchaseForm } from "./AccountingPurchaseForm";

export const dynamic = "force-dynamic";

export default async function AccountingPage() {
  let data: AccountingData | null = null;
  let error: string | null = null;

  try {
    data = await getAccountingData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Administratie"
        description="Verzamel verkoop, inkoop, bonnetjes en btw-controles op een plek. Dit is een hulpmiddel voor je administratie, geen vervanging van fiscaal advies."
      />
      {error || !data ? <AccountingError message={error || "Geen administratiedata beschikbaar"} /> : <AccountingContent data={data} />}
    </AppShell>
  );
}

function AccountingError({ message }: { message: string }) {
  return (
    <SectionCard title="Administratie niet bereikbaar" description="Controleer of de FastAPI backend draait en de migraties zijn uitgevoerd.">
      <EmptyState title="Geen administratiedata" description={message} />
    </SectionCard>
  );
}

function AccountingContent({ data }: { data: AccountingData }) {
  const missingDocs = data.vatSummary.missing_document_count;
  const vatTone = data.vatSummary.vat_due >= 0 ? "warning" : "good";

  return (
    <div className="space-y-6">
      <SectionCard title="Wat doe ik hier?" description="Deze module helpt administratie vastleggen en exporteerbaar maken. Laat aangiftekeuzes controleren door je boekhouder of fiscalist.">
        <div className="grid gap-3 md:grid-cols-3">
          <Step title="1. Verkoopboek" text="Orders en facturen worden hier verkoopregels met netto, btw en bruto bedrag." />
          <Step title="2. Inkoopboek" text="Filament, verpakking, onderdelen en verzendkosten worden kostenregels met bon/factuur." />
          <Step title="3. Btw-controle" text="De app telt verkoop-btw en voorbelasting op en signaleert ontbrekende documenten." />
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Omzet excl. btw" value={formatCurrency(data.vatSummary.sales_net)} note={`${data.vatSummary.sales_count} verkoopregels`} />
        <MetricCard label="Kosten excl. btw" value={formatCurrency(data.vatSummary.purchase_net)} note={`${data.vatSummary.purchase_count} inkoopregels`} />
        <MetricCard label="Verkoop-btw" value={formatCurrency(data.vatSummary.sales_vat)} note="te betalen btw" tone="warning" />
        <MetricCard label="Voorbelasting" value={formatCurrency(data.vatSummary.purchase_vat)} note="terug te vragen btw" tone="good" />
        <MetricCard label="Btw saldo" value={formatCurrency(data.vatSummary.vat_due)} note={data.vatSummary.vat_due >= 0 ? "indicatie te betalen" : "indicatie teruggaaf"} tone={vatTone} />
      </div>

      <SectionCard title="Administratiecontrole" description="Eerste controles voordat je exporteert of aangifte voorbereidt.">
        <div className="grid gap-3 md:grid-cols-3">
          <Check title="Bewaarplicht" text="Bewaar facturen, bonnen en basisadministratie minimaal 7 jaar." status="controle nodig" />
          <Check title="Ontbrekende documenten" text={`${missingDocs} boeking(en) hebben nog geen gekoppeld document.`} status={missingDocs ? "actie nodig" : "op orde"} />
          <Check title="Audit trail" text="Correcties horen als nieuwe correctieregel of creditfactuur, niet als stille wijziging." status="ontwerpregel" />
        </div>
      </SectionCard>

      <SectionCard title="Inkoopboeking toevoegen" description="Leg filament, verpakking, printeronderdelen, software of verzendkosten vast met bon of factuur.">
        <AccountingPurchaseForm />
      </SectionCard>

      <SectionCard title="Documenten" description="Bonnen en facturen die aan verkoop- of inkoopboekingen zijn gekoppeld.">
        {data.documents.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Bestand</th>
                  <th>Type</th>
                  <th>Gekoppeld aan</th>
                  <th>Status</th>
                  <th>Actie</th>
                </tr>
              </thead>
              <tbody>
                {data.documents.slice(0, 50).map((document) => {
                  const purchase = document.purchase_id ? data.purchases.find((item) => item.id === document.purchase_id) : null;
                  const sale = document.sale_id ? data.sales.find((item) => item.id === document.sale_id) : null;
                  return (
                    <tr key={document.id}>
                      <td>{formatDate(document.created_at)}</td>
                      <td className="font-semibold">{document.original_filename || `Document ${document.id}`}</td>
                      <td>{document.document_type}</td>
                      <td>{purchase ? `Inkoop: ${purchase.supplier_name}` : sale ? `Verkoop: ${sale.invoice_number || sale.customer_name || sale.id}` : "-"}</td>
                      <td><StatusBadge status={document.status} /></td>
                      <td>
                        <a className="font-bold text-brand hover:text-ink" href={document.file_path} target="_blank" rel="noreferrer">
                          Openen
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Nog geen documenten" description="Upload een bon of factuur bij een inkoopboeking. Daarna verschijnt die hier." />
        )}
      </SectionCard>

      <SectionCard title="Verkoopboek" description="Verkoopregels uit orders, platformen of handmatige facturen.">
        {data.sales.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Factuur</th>
                  <th>Klant</th>
                  <th className="text-right">Netto</th>
                  <th className="text-right">Btw</th>
                  <th className="text-right">Bruto</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.sales.slice(0, 30).map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.invoice_date)}</td>
                    <td className="font-semibold">{item.invoice_number || `Verkoop ${item.id}`}</td>
                    <td>{item.customer_name || "-"}</td>
                    <td className="text-right">{formatCurrency(item.net_amount)}</td>
                    <td className="text-right">{formatCurrency(item.vat_amount)}</td>
                    <td className="text-right font-semibold">{formatCurrency(item.gross_amount)}</td>
                    <td><StatusBadge status={item.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Nog geen verkoopboek" description="Volgende stap: orders automatisch omzetten naar verkoopboekingen." />
        )}
      </SectionCard>

      <SectionCard title="Inkoopboek" description="Kosten zoals filament, verpakking, printeronderdelen, software en verzending.">
        {data.purchases.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Leverancier</th>
                  <th>Categorie</th>
                  <th className="text-right">Netto</th>
                  <th className="text-right">Btw</th>
                  <th className="text-right">Bruto</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.purchases.slice(0, 30).map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.invoice_date)}</td>
                    <td className="font-semibold">{item.supplier_name}</td>
                    <td>{item.category}</td>
                    <td className="text-right">{formatCurrency(item.net_amount)}</td>
                    <td className="text-right">{formatCurrency(item.vat_amount)}</td>
                    <td className="text-right font-semibold">{formatCurrency(item.gross_amount)}</td>
                    <td><StatusBadge status={item.payment_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Nog geen inkoopboek" description="Volgende stap: handmatig kosten en bonnetjes kunnen toevoegen." />
        )}
      </SectionCard>
    </div>
  );
}

function Step({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md border-l-4 border-brand bg-slate-50 px-4 py-4">
      <div className="font-bold text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  );
}

function Check({ title, text, status }: { title: string; text: string; status: string }) {
  return (
    <div className="rounded-lg border border-line bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-bold text-ink">{title}</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
        </div>
        <StatusBadge status={status} />
      </div>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("nl-NL");
}
