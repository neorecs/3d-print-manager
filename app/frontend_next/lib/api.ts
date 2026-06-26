import {
  DashboardData,
  FilamentSpool,
  Order,
  Platform,
  PrintJob,
  Product,
  ProductInventory,
  ProductPublication,
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
