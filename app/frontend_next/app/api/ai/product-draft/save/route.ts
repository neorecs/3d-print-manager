import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

type Platform = {
  id: number;
  name: string;
  type: string;
};

type DraftVariant = {
  variant_name?: string;
  sku?: string;
  color?: string | null;
  material?: string | null;
  size?: string | null;
  finish?: string | null;
  estimated_print_time_minutes?: number | null;
  estimated_filament_grams?: number | null;
  default_sale_price?: number | null;
  active?: boolean;
};

async function backend(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  if (!response.ok) {
    throw new Error(data?.detail || `Backendfout ${response.status} op ${path}`);
  }
  return data;
}

function normalizeSku(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48)
    .toUpperCase();
}

function publicationForPlatform(platforms: Platform[], key: string) {
  const normalized = key.trim().toLowerCase();
  return platforms.find(
    (platform) =>
      platform.type.toLowerCase() === normalized ||
      platform.name.toLowerCase() === normalized ||
      platform.name.toLowerCase().includes(normalized),
  );
}

export async function POST(request: NextRequest) {
  const draft = await request.json();
  const productDraft = draft?.product;

  if (!productDraft?.name && !productDraft?.internal_title) {
    return NextResponse.json({ detail: "Concept mist productnaam of titel" }, { status: 400 });
  }

  const created = {
    product: null as Record<string, unknown> | null,
    tags: [] as Record<string, unknown>[],
    variants: [] as Record<string, unknown>[],
    publications: [] as Record<string, unknown>[],
  };
  const warnings: string[] = [];

  try {
    const product = await backend("/products", {
      method: "POST",
      body: JSON.stringify({
        name: productDraft.name || productDraft.internal_title,
        internal_title: productDraft.internal_title || productDraft.name,
        short_description: productDraft.short_description || null,
        long_description: productDraft.long_description || null,
        sales_description: productDraft.sales_description || null,
        seo_title: productDraft.seo_title || null,
        seo_description: productDraft.seo_description || null,
        product_type: productDraft.product_type || null,
        internal_category: productDraft.internal_category || null,
        status: "concept",
        active: productDraft.active !== false,
      }),
    });
    created.product = product;
    const productId = Number(product.id);

    for (const tag of Array.isArray(draft.tags) ? draft.tags : []) {
      const cleaned = String(tag || "").trim();
      if (!cleaned) continue;
      try {
        const createdTag = await backend(`/products/${productId}/tags`, {
          method: "POST",
          body: JSON.stringify({ tag: cleaned }),
        });
        created.tags.push(createdTag);
      } catch (caught) {
        warnings.push(`Tag '${cleaned}' kon niet worden opgeslagen: ${caught instanceof Error ? caught.message : "onbekende fout"}`);
      }
    }

    const variants = Array.isArray(draft.variants) ? draft.variants : [];
    for (const [index, variant] of variants.entries() as IterableIterator<[number, DraftVariant]>) {
      const fallbackName = variant.variant_name || `Variant ${index + 1}`;
      const sku = variant.sku || normalizeSku(`${productDraft.internal_title || productDraft.name}-${fallbackName}-${index + 1}`);
      try {
        const createdVariant = await backend("/product-variants", {
          method: "POST",
          body: JSON.stringify({
            product_id: productId,
            variant_name: fallbackName,
            sku,
            color: variant.color || null,
            material: variant.material || null,
            size: variant.size || null,
            finish: variant.finish || null,
            print_file_path: null,
            estimated_print_time_minutes: variant.estimated_print_time_minutes ?? null,
            estimated_filament_grams: variant.estimated_filament_grams ?? null,
            weight_grams: null,
            length_mm: null,
            width_mm: null,
            height_mm: null,
            default_sale_price: variant.default_sale_price ?? null,
            action_sale_price: null,
            cost_price: null,
            active: variant.active !== false,
          }),
        });
        created.variants.push(createdVariant);
      } catch (caught) {
        warnings.push(`Variant '${fallbackName}' kon niet worden opgeslagen: ${caught instanceof Error ? caught.message : "onbekende fout"}`);
      }
    }

    const platforms = (await backend("/platforms")) as Platform[];
    const publications = draft.platform_publications && typeof draft.platform_publications === "object" ? draft.platform_publications : {};
    for (const [platformKey, publication] of Object.entries(publications) as [string, Record<string, unknown>][]) {
      const platform = publicationForPlatform(platforms, platformKey);
      if (!platform) {
        warnings.push(`Geen platform gevonden voor '${platformKey}'. Publicatieconcept overgeslagen.`);
        continue;
      }
      try {
        const createdPublication = await backend(`/products/${productId}/publications`, {
          method: "POST",
          body: JSON.stringify({
            platform_id: platform.id,
            external_product_id: null,
            external_listing_id: null,
            publication_status: "concept",
            platform_title: publication.platform_title || productDraft.internal_title || productDraft.name,
            platform_description: publication.platform_description || productDraft.sales_description || productDraft.short_description || null,
            platform_category: publication.platform_category || productDraft.internal_category || null,
            platform_tags: publication.platform_tags || (Array.isArray(draft.tags) ? draft.tags.join(", ") : null),
            platform_price_override: publication.platform_price_override ?? null,
            platform_shipping_profile_id: null,
            last_synced_at: null,
            last_error: null,
          }),
        });
        created.publications.push(createdPublication);
      } catch (caught) {
        warnings.push(`Publicatie voor '${platformKey}' kon niet worden opgeslagen: ${caught instanceof Error ? caught.message : "onbekende fout"}`);
      }
    }

    return NextResponse.json({
      status: warnings.length ? "partial" : "created",
      product_id: productId,
      created,
      warnings,
    });
  } catch (caught) {
    return NextResponse.json(
      {
        detail: caught instanceof Error ? caught.message : "Concept opslaan is mislukt",
        created,
        warnings,
      },
      { status: 500 },
    );
  }
}
