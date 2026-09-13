import { AppShell } from "@/components/AppShell";
import { CollapsibleHelp } from "@/components/CollapsibleHelp";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatCurrency, getAccountingData } from "@/lib/api";
import type { AccountingData } from "@/lib/types";
import { ArchiveDocumentButton, CorrectionButton, FiscalSettingsForm, VatPeriodCloseForm } from "./AccountingControls";
import { AccountingPurchaseForm } from "./AccountingPurchaseForm";
import { AccountingSaleForm } from "./AccountingSaleForm";

export const dynamic = "force-dynamic";

export default async function AccountingPage({ searchParams }: { searchParams: Promise<{ start_date?: string; end_date?: string }> }) {
  const params = await searchParams;
  const filters = {
    startDate: normalizeDateParam(params.start_date),
    endDate: normalizeDateParam(params.end_date),
  };
  let data: AccountingData | null = null;
  let error: string | null = null;

  try {
    data = await getAccountingData(filters);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Administratie"
        description="Verzamel verkoop, inkoop, bonnetjes en btw-controles op een plek. Dit is een hulpmiddel voor je administratie, geen vervanging van fiscaal advies."
      />
      {error || !data ? <AccountingError message={error || "Geen administratiedata beschikbaar"} /> : <AccountingContent data={data} filters={filters} />}
    </AppShell>
  );
}

function AccountingError({ message }: { message: string }) {
  return <ErrorState message={message} retryHref="/administratie" title="Administratie kon niet worden geladen" />;
}

function AccountingContent({ data, filters }: { data: AccountingData; filters: { startDate?: string; endDate?: string } }) {
  const missingDocs = data.vatSummary.missing_document_count;
  const vatTone = data.vatSummary.vat_due >= 0 ? "warning" : "good";
  const exportQuery = buildAccountingQuery(filters);

  return (
    <div className="space-y-6">
      <CollapsibleHelp>
        <p>Leg vooral bonnetjes en inkopen vast. Orders vullen het verkoopboek aan; de app telt daarna btw en ontbrekende documenten op. Laat aangiftekeuzes controleren door je boekhouder of fiscalist.</p>
      </CollapsibleHelp>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Omzet excl. btw" value={formatCurrency(data.vatSummary.sales_net)} note={`${data.vatSummary.sales_count} verkoopregels`} />
        <MetricCard label="Kosten excl. btw" value={formatCurrency(data.vatSummary.purchase_net)} note={`${data.vatSummary.purchase_count} inkoopregels`} />
        <MetricCard label="Verkoop-btw" value={formatCurrency(data.vatSummary.sales_vat)} note="te betalen btw" tone="warning" />
        <MetricCard label="Voorbelasting" value={formatCurrency(data.vatSummary.purchase_vat)} note="terug te vragen btw" tone="good" />
        <MetricCard label="Btw saldo" value={formatCurrency(data.vatSummary.vat_due)} note={data.vatSummary.vat_due >= 0 ? "indicatie te betalen" : "indicatie teruggaaf"} tone={vatTone} />
      </div>

      <SectionCard title="Bon of inkoop toevoegen" description="Leg filament, verpakking, printeronderdelen, software of verzendkosten vast met bon of factuur.">
        <AccountingPurchaseForm />
      </SectionCard>

      <SectionCard title="Periode bekijken" description="Filter verkoopboek, inkoopboek, btw-cijfers en CSV-exports op factuurdatum. Laat leeg om alles te tonen.">
        <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto_auto]" action="/administratie">
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Vanaf</span>
            <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" defaultValue={filters.startDate || ""} name="start_date" type="date" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-bold text-slate-300">Tot en met</span>
            <input className="w-full rounded-md border border-line bg-slate-950/35 px-3 py-2 text-sm text-ink outline-none focus:border-brand" defaultValue={filters.endDate || ""} name="end_date" type="date" />
          </label>
          <div className="flex items-end">
            <button className="w-full rounded-md bg-brand px-4 py-2 text-sm font-black text-slate-950" type="submit">Filter toepassen</button>
          </div>
          <div className="flex items-end">
            <a className="w-full rounded-md border border-line bg-slate-950/35 px-4 py-2 text-center text-sm font-bold text-slate-300 hover:bg-white/5" href="/administratie">Alles tonen</a>
          </div>
        </form>
      </SectionCard>

      <SectionCard title="Administratiecontrole" description="Eerste controles voordat je exporteert of aangifte voorbereidt.">
        <div className="grid gap-3 md:grid-cols-3">
          <Check title="Bewaarplicht" text="Bewaar facturen, bonnen en basisadministratie minimaal 7 jaar." status="controle nodig" />
          <Check title="Ontbrekende documenten" text={`${missingDocs} boeking(en) hebben nog geen gekoppeld document.`} status={missingDocs ? "actie nodig" : "op orde"} />
          <Check title="Audit trail" text="Correcties horen als nieuwe correctieregel of creditfactuur, niet als stille wijziging." status="ontwerpregel" />
        </div>
      </SectionCard>

      <SectionCard title="Fiscale instellingen" description="Leg expliciet vast welke fiscale aannames de app gebruikt. Controleer dit met je boekhouder of fiscalist.">
        <details className="rounded-lg border border-line bg-panelSoft p-4">
          <summary className="cursor-pointer list-none font-bold text-ink">Fiscale instellingen wijzigen</summary>
          <div className="mt-4 border-t border-line pt-4"><FiscalSettingsForm settings={data.fiscalSettings} /></div>
        </details>
      </SectionCard>

      <SectionCard title="Export voor boekhouder" description="Download CSV-bestanden met de huidige verkoopregels, inkoopregels en btw-samenvatting. Controleer fiscale keuzes voordat je dit gebruikt voor aangifte.">
        <div className="flex flex-wrap gap-3">
          <ExportLink href={`/api/accounting/export/sales${exportQuery}`} label="Verkoopboek CSV" />
          <ExportLink href={`/api/accounting/export/purchases${exportQuery}`} label="Inkoopboek CSV" />
          <ExportLink href={`/api/accounting/export/vat-summary${exportQuery}`} label="Btw-samenvatting CSV" />
        </div>
      </SectionCard>

      <SectionCard title="Btw-periode afsluiten" description="Leg de btw-samenvatting voor de geselecteerde periode vast. Afgesloten perioden worden niet stil overschreven.">
        {data.vatPeriods.length ? (
          <div className="mt-5 table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Periode</th>
                  <th>Datums</th>
                  <th className="text-right">Verkoop-btw</th>
                  <th className="text-right">Voorbelasting</th>
                  <th className="text-right">Saldo</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.vatPeriods.slice(0, 10).map((period) => (
                  <tr key={period.id}>
                    <td className="font-semibold">{period.period_name}</td>
                    <td>{formatDate(period.start_date)} - {formatDate(period.end_date)}</td>
                    <td className="text-right">{formatCurrency(period.sales_vat)}</td>
                    <td className="text-right">{formatCurrency(period.purchase_vat)}</td>
                    <td className="text-right font-semibold">{formatCurrency(period.vat_due)}</td>
                    <td><StatusBadge status={period.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <details className="mt-4 rounded-lg border border-line bg-panelSoft p-4">
          <summary className="cursor-pointer list-none font-bold text-ink">Nieuwe btw-periode afsluiten</summary>
          <div className="mt-4 border-t border-line pt-4"><VatPeriodCloseForm endDate={filters.endDate} startDate={filters.startDate} /></div>
        </details>
      </SectionCard>

      <SectionCard title="Verkoopboeking toevoegen" description="Gebruik dit alleen voor handmatige verkopen of correcties buiten de automatische orderflow. Orders boek je bij voorkeur vanuit orderdetail.">
        <details className="rounded-lg border border-line bg-panelSoft p-4">
          <summary className="cursor-pointer list-none font-bold text-ink">Handmatige verkoop toevoegen</summary>
          <div className="mt-4 border-t border-line pt-4"><AccountingSaleForm /></div>
        </details>
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
                  <th>Beheer</th>
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
                        <a className="font-bold text-brand hover:text-white" href={document.file_path} target="_blank" rel="noreferrer">
                          Openen
                        </a>
                      </td>
                      <td><ArchiveDocumentButton disabled={document.status === "gearchiveerd"} id={document.id} /></td>
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
                  <th>Bron</th>
                  <th>Correctie</th>
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
                    <td>
                      {item.order_id ? (
                        <a className="font-bold text-brand hover:text-white" href={`/orders/${item.order_id}`}>
                          Order {item.order_id}
                        </a>
                      ) : (
                        formatAccountingSource(item.source)
                      )}
                    </td>
                    <td><CorrectionButton disabled={item.entry_type === "credit" || item.status === "gecorrigeerd"} id={item.id} type="sale" /></td>
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
                  <th>Correctie</th>
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
                    <td><CorrectionButton disabled={item.entry_type === "correction" || item.payment_status === "gecorrigeerd"} id={item.id} type="purchase" /></td>
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

function Check({ title, text, status }: { title: string; text: string; status: string }) {
  return (
    <div className="rounded-xl border border-line bg-panelSoft p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-black text-ink">{title}</div>
          <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
        </div>
        <StatusBadge status={status} />
      </div>
    </div>
  );
}

function ExportLink({ href, label }: { href: string; label: string }) {
  return (
    <a className="rounded-md border border-line bg-slate-950/35 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-white/5" download href={href}>
      {label}
    </a>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("nl-NL");
}

function formatAccountingSource(value?: string | null) {
  const labels: Record<string, string> = {
    order_inventory_check: "Automatisch vanuit ordercontrole",
    order: "Automatisch vanuit order",
    manual: "Handmatig toegevoegd",
    handmatig: "Handmatig toegevoegd",
  };
  return value ? labels[value] || value.replaceAll("_", " ") : "Handmatig toegevoegd";
}

function normalizeDateParam(value?: string) {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined;
}

function buildAccountingQuery(filters: { startDate?: string; endDate?: string }) {
  const params = new URLSearchParams();
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);
  const query = params.toString();
  return query ? `?${query}` : "";
}
