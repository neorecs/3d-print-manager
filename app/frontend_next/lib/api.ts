import {
  DashboardData,
  FilamentSpool,
  Order,
  Platform,
  PrintJob,
  Product,
  ProductCatalogData,
  ProductDetailData,
  ProductInventory,
  ProductMedia,
  ProductPublication,
  ProductTag,
  ProductVariant,
  StockRecommendation,
} from "./types";

const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API-fout ${response.status} op ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardData(): Promise<DashboardData> {
  const [products, platforms, orders, inventory, filament, printJobs, recommendations] = await Promise.all([
    apiGet<Product[]>("/products"),
    apiGet<Platform[]>("/platforms"),
    apiGet<Order[]>("/orders"),
    apiGet<ProductInventory[]>("/inventory/products"),
    apiGet<FilamentSpool[]>("/filament"),
    apiGet<PrintJob[]>("/print-jobs"),
    apiGet<StockRecommendation[]>("/stock-recommendations"),
  ]);

  const publicationsNested = await Promise.all(
    products.slice(0, 30).map((product) =>
      apiGet<ProductPublication[]>(`/products/${product.id}/publications`).catch(() => []),
    ),
  );

  return {
    products,
    platforms,
    orders,
    inventory,
    filament,
    printJobs,
    recommendations,
    publications: publicationsNested.flat(),
  };
}

export async function getProductCatalogData(): Promise<ProductCatalogData> {
  const [products, variants, inventory, platforms] = await Promise.all([
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<ProductInventory[]>("/inventory/products"),
    apiGet<Platform[]>("/platforms"),
  ]);

  const publicationsNested = await Promise.all(
    products.map((product) => apiGet<ProductPublication[]>(`/products/${product.id}/publications`).catch(() => [])),
  );
  const publications = publicationsNested.flat();

  return {
    products,
    variants,
    inventory,
    platforms,
    rows: products.map((product) => ({
      product,
      variants: variants.filter((variant) => variant.product_id === product.id),
      inventory: inventory.filter((item) => item.product_id === product.id),
      publications: publications.filter((publication) => publication.product_id === product.id),
    })),
  };
}

export async function getProductDetailData(productId: number): Promise<ProductDetailData> {
  const [product, variants, inventory, media, tags, publications, platforms] = await Promise.all([
    apiGet<Product>(`/products/${productId}`),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<ProductInventory[]>("/inventory/products"),
    apiGet<ProductMedia[]>(`/products/${productId}/media`).catch(() => []),
    apiGet<ProductTag[]>(`/products/${productId}/tags`).catch(() => []),
    apiGet<ProductPublication[]>(`/products/${productId}/publications`).catch(() => []),
    apiGet<Platform[]>("/platforms"),
  ]);

  return {
    product,
    variants: variants.filter((variant) => variant.product_id === productId),
    inventory: inventory.filter((item) => item.product_id === productId),
    media,
    tags,
    publications,
    platforms,
  };
}

export function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat("nl-NL", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

export function formatMinutes(value: number) {
  if (value < 60) {
    return `${value} min`;
  }

  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours}u ${minutes}m` : `${hours}u`;
}
