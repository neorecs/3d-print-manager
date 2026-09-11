import type { ProductCatalogRow } from "./types";

export function catalogRows(rows: ProductCatalogRow[], view: string) {
  return rows.filter(({ product }) => {
    const archived = product.active === false || product.status === "gearchiveerd";
    return view === "alle" || (view === "archief" ? archived : !archived);
  });
}

export function salesBasicsMissing(row: ProductCatalogRow): string[] {
  const missing: string[] = [];
  const variants = row.variants.filter((variant) => variant.active !== false);
  if (!(row.product.internal_title || row.product.name)?.trim()) missing.push("titel");
  if (!(row.product.short_description || row.product.long_description)?.trim()) missing.push("omschrijving");
  if (!variants.length) missing.push("variant");
  if (variants.some((variant) => !variant.sku?.trim() || !(Number(variant.default_sale_price) > 0))) missing.push("SKU of prijs");
  if (variants.some((variant) => !variant.material?.trim() || !variant.color?.trim())) missing.push("materiaal of kleur");
  return missing;
}
