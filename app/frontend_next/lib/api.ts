import {
  AccountingData,
  AccountingDocument,
  AccountingPurchase,
  AccountingSale,
  AIProductStatus,
  AnalyticsData,
  AnalyticsRow,
  BambuPrinter,
  BambuPrintersData,
  CostSetting,
  DashboardData,
  FilamentSpool,
  FilamentData,
  InventoryData,
  InventoryMovement,
  Order,
  OrderDetail,
  OrderDetailData,
  OrderItem,
  OrdersData,
  Platform,
  PlatformConnectorStatus,
  PlatformCredential,
  PrintBatch,
  PrintJob,
  PrintPlanningData,
  Product,
  ProductCatalogData,
  ProductDetailData,
  ProductInventory,
  ProductMedia,
  ProductPublication,
  ProductTag,
  ProductVariant,
  SalesChannelDetailData,
  SalesChannelsData,
  StockRecommendation,
  VatPeriod,
  VatSummary,
} from "./types";

function getApiBaseUrl() {
  return process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
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

export async function getOrdersData(): Promise<OrdersData> {
  const [orders, orderItems, platforms, products, variants, printJobs] = await Promise.all([
    apiGet<Order[]>("/orders"),
    apiGet<OrderItem[]>("/order-items"),
    apiGet<Platform[]>("/platforms"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<PrintJob[]>("/print-jobs"),
  ]);

  return {
    orders,
    orderItems,
    platforms,
    products,
    variants,
    printJobs,
  };
}

export async function getOrderDetailData(orderId: number): Promise<OrderDetailData> {
  const [order, platforms, products, variants, printJobs] = await Promise.all([
    apiGet<OrderDetail>(`/orders/${orderId}`),
    apiGet<Platform[]>("/platforms"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<PrintJob[]>("/print-jobs"),
  ]);

  return {
    order,
    platform: platforms.find((platform) => platform.id === order.platform_id) || null,
    products,
    variants,
    printJobs: printJobs.filter((job) => order.items.some((item) => item.id === job.order_item_id)),
  };
}

export async function getPrintPlanningData(): Promise<PrintPlanningData> {
  const [printJobs, printBatches, products, variants, orders, orderItems] = await Promise.all([
    apiGet<PrintJob[]>("/print-jobs"),
    apiGet<PrintBatch[]>("/print-batches"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<Order[]>("/orders"),
    apiGet<OrderItem[]>("/order-items"),
  ]);

  return {
    printJobs,
    printBatches,
    products,
    variants,
    orders,
    orderItems,
  };
}

export async function getFilamentData(): Promise<FilamentData> {
  const [filament, printJobs] = await Promise.all([
    apiGet<FilamentSpool[]>("/filament"),
    apiGet<PrintJob[]>("/print-jobs"),
  ]);

  return {
    filament,
    printJobs,
  };
}

export async function getInventoryData(): Promise<InventoryData> {
  const [inventory, movements, products, variants] = await Promise.all([
    apiGet<ProductInventory[]>("/inventory/products"),
    apiGet<InventoryMovement[]>("/inventory/movements"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
  ]);

  return { inventory, movements, products, variants };
}

export async function getBambuPrintersData(): Promise<BambuPrintersData> {
  const printers = await apiGet<BambuPrinter[]>("/bambu/printers");
  return { printers };
}

export async function getAccountingData(): Promise<AccountingData> {
  const [sales, purchases, documents, vatSummary, vatPeriods] = await Promise.all([
    apiGet<AccountingSale[]>("/accounting/sales"),
    apiGet<AccountingPurchase[]>("/accounting/purchases"),
    apiGet<AccountingDocument[]>("/accounting/documents"),
    apiGet<VatSummary>("/accounting/vat-summary"),
    apiGet<VatPeriod[]>("/accounting/vat-periods"),
  ]);

  return { sales, purchases, documents, vatSummary, vatPeriods };
}

export async function getSalesChannelsData(): Promise<SalesChannelsData> {
  const [platforms, products] = await Promise.all([
    apiGet<Platform[]>("/platforms"),
    apiGet<Product[]>("/products"),
  ]);

  const [statuses, publicationsNested] = await Promise.all([
    Promise.all(platforms.map((platform) => apiGet<PlatformConnectorStatus>(`/platforms/${platform.id}/connector-status`).catch(() => null))),
    Promise.all(products.map((product) => apiGet<ProductPublication[]>(`/products/${product.id}/publications`).catch(() => []))),
  ]);

  return {
    platforms,
    statuses: statuses.filter((status): status is PlatformConnectorStatus => Boolean(status)),
    products,
    publications: publicationsNested.flat(),
  };
}

export async function getSalesChannelDetailData(platformId: number): Promise<SalesChannelDetailData> {
  const [platforms, status, credentials, products] = await Promise.all([
    apiGet<Platform[]>("/platforms"),
    apiGet<PlatformConnectorStatus>(`/platforms/${platformId}/connector-status`).catch(() => null),
    apiGet<PlatformCredential[]>(`/platforms/${platformId}/credentials`).catch(() => []),
    apiGet<Product[]>("/products"),
  ]);

  const platform = platforms.find((item) => item.id === platformId);
  if (!platform) {
    throw new Error(`Verkoopkanaal ${platformId} niet gevonden`);
  }

  const publicationsNested = await Promise.all(
    products.map((product) => apiGet<ProductPublication[]>(`/products/${product.id}/publications`).catch(() => [])),
  );

  return {
    platform,
    status,
    credentials,
    products,
    publications: publicationsNested.flat().filter((publication) => publication.platform_id === platformId),
  };
}

export async function getAnalyticsData(periodDays = 30): Promise<AnalyticsData> {
  const [salesTrends, topProducts, topColors, topMaterials, recommendations, costSettings] = await Promise.all([
    apiGet<AnalyticsRow[]>(`/analytics/sales-trends?period_days=${periodDays}`),
    apiGet<AnalyticsRow[]>(`/analytics/top-products?period_days=${periodDays}`),
    apiGet<AnalyticsRow[]>(`/analytics/top-colors?period_days=${periodDays}`),
    apiGet<AnalyticsRow[]>(`/analytics/top-materials?period_days=${periodDays}`),
    apiGet<StockRecommendation[]>("/stock-recommendations"),
    apiGet<CostSetting[]>("/cost-settings"),
  ]);

  return { salesTrends, topProducts, topColors, topMaterials, recommendations, costSettings };
}

export async function getAIProductStatus(): Promise<AIProductStatus> {
  try {
    return await apiGet<AIProductStatus>("/ai/product-draft/status");
  } catch {
    return {
      enabled: false,
      configured: false,
      model: "mockmodus",
      ready: false,
      note: "AI-status is niet bereikbaar. De frontend gebruikt gratis mockmodus zonder OpenAI API-call.",
    };
  }
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
