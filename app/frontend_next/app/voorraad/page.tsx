import { AppShell } from "@/components/AppShell";
import { CollapsibleHelp } from "@/components/CollapsibleHelp";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { SectionCard } from "@/components/SectionCard";
import { StatusBadge } from "@/components/StatusBadge";
import { getInventoryData } from "@/lib/api";
import type { InventoryData, ProductInventory } from "@/lib/types";

export default async function InventoryPage() {
  let data: InventoryData | null = null;
  let error: string | null = null;

  try {
    data = await getInventoryData();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Backend niet bereikbaar";
  }

  return (
    <AppShell>
      <PageHeader
        title="Productvoorraad"
        description="Beheer geprinte producten die klaar liggen voor verkoop, verzending of reservering."
        actions={<a className="rounded-xl border border-line px-4 py-2 text-sm font-black text-slate-200 hover:bg-white/5" href="/catalogus">Naar catalogus</a>}
      />
      {error || !data ? <InventoryError message={error || "Geen voorraaddata beschikbaar"} /> : <InventoryContent data={data} />}
    </AppShell>
  );
}

function InventoryError({ message }: { message: string }) {
  return <ErrorState message={message} retryHref="/voorraad" title="Voorraad kon niet worden geladen" />;
}

function InventoryContent({ data }: { data: InventoryData }) {
  const freeStock = data.inventory.reduce((total, item) => total + free(item), 0);
  const reserved = data.inventory.reduce((total, item) => total + Number(item.quantity_reserved || 0), 0);
  const lowRows = data.inventory.filter((item) => free(item) <= Number(item.minimum_stock_level || 0));
  const shortageRows = data.inventory.filter((item) => free(item) < 0);

  return (
    <div className="space-y-6">
      <CollapsibleHelp><p>Productvoorraad bestaat uit producten die al geprint zijn. Vrije voorraad is wat op voorraad ligt min reserveringen voor orders. Minimumvoorraad en alle bewegingen blijven traceerbaar. Filamentrollen beheer je apart onder <a className="font-bold text-brand" href="/filament">Filament</a>.</p></CollapsibleHelp>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Voorraadregels" value={data.inventory.length} note="productvarianten" />
        <MetricCard label="Vrije voorraad" value={freeStock} note="klaar voor verkoop" tone="good" />
        <MetricCard label="Gereserveerd" value={reserved} note="gekoppeld aan orders" />
        <MetricCard label="Lage voorraad" value={lowRows.length} note="op of onder minimum" tone={lowRows.length ? "warning" : "good"} />
        <MetricCard label="Tekort" value={shortageRows.length} note="negatieve vrije voorraad" tone={shortageRows.length ? "danger" : "good"} />
      </div>

      <SectionCard title="Voorraadregels" description="Open het product om voorraadregels inhoudelijk te wijzigen.">
        {data.inventory.length ? (
          <div className="table-scroll">
            <table className="data-table data-table-responsive">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Variant</th>
                  <th>Kleur</th>
                  <th>Materiaal</th>
                  <th className="text-right">Op voorraad</th>
                  <th className="text-right">Gereserveerd</th>
                  <th className="text-right">Vrij</th>
                  <th>Status</th>
                  <th>Locatie</th>
                </tr>
              </thead>
              <tbody>
                {data.inventory.map((item) => {
                  const product = data.products.find((row) => row.id === item.product_id);
                  const variant = data.variants.find((row) => row.id === item.product_variant_id);
                  const low = free(item) <= Number(item.minimum_stock_level || 0);
                  return (
                    <tr key={item.id}>
                      <td className="font-semibold" data-label="Product"><a className="hover:text-brand" href={`/catalogus/${item.product_id}`}>{product?.internal_title || product?.name || `Product ${item.product_id}`}</a></td>
                      <td data-label="Variant">{variant?.variant_name || variant?.sku || `Variant ${item.product_variant_id}`}</td>
                      <td data-label="Kleur">{item.color || variant?.color || "-"}</td>
                      <td data-label="Materiaal">{item.material || variant?.material || "-"}</td>
                      <td className="text-right" data-label="Op voorraad">{item.quantity_on_hand}</td>
                      <td className="text-right" data-label="Gereserveerd">{item.quantity_reserved}</td>
                      <td className="text-right font-bold" data-label="Vrij">{free(item)}</td>
                      <td data-label="Status"><StatusBadge status={low ? "lage voorraad" : "voldoende"} /></td>
                      <td data-label="Locatie">{item.location || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Geen productvoorraad" description="Maak voorraadregels aan vanuit een productdetailpagina." />
        )}
      </SectionCard>

      <SectionCard title="Laatste voorraadbewegingen" description="Traceerbare wijzigingen uit orders, printresultaten en correcties.">
        {data.movements.length ? (
          <div className="table-scroll">
            <table className="data-table data-table-responsive">
              <thead>
                <tr>
                  <th>Moment</th>
                  <th>Type</th>
                  <th className="text-right">Aantal</th>
                  <th>Bron</th>
                  <th>Notitie</th>
                </tr>
              </thead>
              <tbody>
                {data.movements.slice(0, 25).map((item) => (
                  <tr key={item.id}>
                    <td data-label="Moment">{item.created_at ? new Date(item.created_at).toLocaleString("nl-NL") : "-"}</td>
                    <td data-label="Beweging"><StatusBadge status={item.movement_type} /></td>
                    <td className="text-right font-semibold" data-label="Aantal">{item.quantity}</td>
                    <td data-label="Bron">{item.source || (item.print_job_id ? `Printtaak ${item.print_job_id}` : item.order_id ? `Order ${item.order_id}` : "-")}</td>
                    <td data-label="Toelichting">{item.note || item.reason || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Geen voorraadbewegingen" description="Bewegingen verschijnen na reserveringen, correcties of printresultaten." />
        )}
      </SectionCard>
    </div>
  );
}

function free(item: ProductInventory) {
  return Number(item.quantity_on_hand || 0) - Number(item.quantity_reserved || 0);
}

function Step({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-line border-l-4 border-l-brand bg-panelSoft px-4 py-4">
      <div className="font-black text-ink">{title}</div>
      <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
    </div>
  );
}
