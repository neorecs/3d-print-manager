import {
  AccountingData,
  AccountingDocument,
  AccountingFiscalSetting,
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
  PlatformImportLog,
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
  ProductTranslation,
  ProductVariant,
  SalesChannelDetailData,
  SalesChannelsData,
  SalesMarket,
  SearchData,
  StockRecommendation,
  SystemReadiness,
  VatPeriod,
  VatSummary,
} from "./types";
import { backendFetch, getBackendBaseUrl } from "./backend-auth";
import { loadResult } from "./loadResult";
export { formatCurrency, formatMinutes } from "./format";

function getApiBaseUrl() {
  return getBackendBaseUrl();
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await backendFetch(`${getApiBaseUrl()}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API-fout ${response.status} op ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardData(): Promise<DashboardData> {
  const data = await apiGet<{
    metrics: DashboardData["metrics"];
    monthly_revenue: number[];
    printers: BambuPrinter[];
    top_products: DashboardData["topProducts"];
    low_inventory: DashboardData["lowInventory"];
    open_print_jobs: PrintJob[];
  }>("/dashboard/overview");
  return {
    metrics: data.metrics,
    monthlyRevenue: data.monthly_revenue,
    printers: data.printers,
    topProducts: data.top_products,
    lowInventory: data.low_inventory,
    openPrintJobs: data.open_print_jobs,
  };
}

export async function getProductCatalogData(page = 1, view = "actief"): Promise<ProductCatalogData> {
  const [overview, platforms, printers] = await Promise.all([
    apiGet<Omit<ProductCatalogData, "platforms" | "printers" | "printerLoadError" | "pageSize" | "pageCount"> & { page_size: number; page_count: number }>(`/products/overview?page=${page}&page_size=20&view=${encodeURIComponent(view)}`),
    apiGet<Platform[]>("/platforms"),
    loadResult(apiGet<BambuPrinter[]>("/bambu/printers")),
  ]);
  return {
    ...overview,
    pageSize: overview.page_size,
    pageCount: overview.page_count,
    platforms,
    printers: printers.data ?? [],
    printerLoadError: printers.error,
  };
}

export async function getProductDetailData(productId: number): Promise<ProductDetailData> {
  const [product, variants, inventory, media, tags, translations, publications, platforms, printers] = await Promise.all([
    apiGet<Product>(`/products/${productId}`),
    apiGet<ProductVariant[]>(`/product-variants?product_id=${productId}`),
    apiGet<ProductInventory[]>(`/inventory/products?product_id=${productId}`),
    loadResult(apiGet<ProductMedia[]>(`/products/${productId}/media`)),
    loadResult(apiGet<ProductTag[]>(`/products/${productId}/tags`)),
    loadResult(apiGet<ProductTranslation[]>(`/products/${productId}/translations`)),
    loadResult(apiGet<ProductPublication[]>(`/products/${productId}/publications`)),
    apiGet<Platform[]>("/platforms"),
    loadResult(apiGet<BambuPrinter[]>("/bambu/printers")),
  ]);

  return {
    product,
    variants,
    inventory,
    media: media.data ?? [],
    tags: tags.data ?? [],
    translations: translations.data ?? [],
    publications: publications.data ?? [],
    loadErrors: Object.fromEntries(Object.entries({ media, tags, translations, publications, printers }).filter(([, result]) => result.error).map(([key, result]) => [key, result.error])),
    platforms,
    printers: printers.data ?? [],
  };
}

export async function getOrdersData(page = 1, status = "alle"): Promise<OrdersData> {
  const data = await apiGet<{
    orders: Order[]; order_items: OrderItem[]; platforms: Platform[]; print_jobs: PrintJob[];
    import_logs: PlatformImportLog[]; metrics: OrdersData["metrics"];
    page: number; page_size: number; page_count: number; total: number; status: string;
  }>(`/orders/overview?page=${page}&page_size=25&status=${encodeURIComponent(status)}`);
  return {
    orders: data.orders,
    orderItems: data.order_items,
    platforms: data.platforms,
    printJobs: data.print_jobs,
    importLogs: data.import_logs,
    metrics: data.metrics,
    page: data.page,
    pageSize: data.page_size,
    pageCount: data.page_count,
    total: data.total,
    status: data.status,
  };
}

export async function getSearchData(query: string): Promise<SearchData> {
  return apiGet<SearchData>(`/search?q=${encodeURIComponent(query)}&limit=20`);
}

export async function getOrderDetailData(orderId: number): Promise<OrderDetailData> {
  const [order, platforms, products, variants, printJobs, sales] = await Promise.all([
    apiGet<OrderDetail>(`/orders/${orderId}`),
    apiGet<Platform[]>("/platforms"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<PrintJob[]>("/print-jobs"),
    apiGet<AccountingSale[]>("/accounting/sales"),
  ]);

  return {
    order,
    platform: platforms.find((platform) => platform.id === order.platform_id) || null,
    accountingSale: sales.find((sale) => sale.order_id === order.id) || null,
    products,
    variants,
    printJobs: printJobs.filter((job) => order.items.some((item) => item.id === job.order_item_id)),
  };
}

export async function getPrintPlanningData(): Promise<PrintPlanningData> {
  const [printJobs, printBatches, products, variants, orders, orderItems, printers] = await Promise.all([
    apiGet<PrintJob[]>("/print-jobs"),
    apiGet<PrintBatch[]>("/print-batches"),
    apiGet<Product[]>("/products"),
    apiGet<ProductVariant[]>("/product-variants"),
    apiGet<Order[]>("/orders"),
    apiGet<OrderItem[]>("/order-items"),
    loadResult(apiGet<BambuPrinter[]>("/bambu/printers")),
  ]);

  return {
    printJobs,
    printBatches,
    products,
    variants,
    orders,
    orderItems,
    printers: printers.data ?? [],
    printerLoadError: printers.error,
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

function buildQuery(params: Record<string, string | undefined | null>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) searchParams.set(key, value);
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function getAccountingData(filters: { startDate?: string; endDate?: string } = {}): Promise<AccountingData> {
  const query = buildQuery({ start_date: filters.startDate, end_date: filters.endDate });
  const [sales, purchases, documents, vatSummary, vatPeriods, fiscalSettings] = await Promise.all([
    apiGet<AccountingSale[]>(`/accounting/sales${query}`),
    apiGet<AccountingPurchase[]>(`/accounting/purchases${query}`),
    apiGet<AccountingDocument[]>("/accounting/documents"),
    apiGet<VatSummary>(`/accounting/vat-summary${query}`),
    apiGet<VatPeriod[]>("/accounting/vat-periods"),
    apiGet<AccountingFiscalSetting[]>("/accounting/fiscal-settings"),
  ]);

  return { sales, purchases, documents, vatSummary, vatPeriods, fiscalSettings };
}

export async function getSalesChannelsData(): Promise<SalesChannelsData> {
  const [platforms, markets, products] = await Promise.all([
    apiGet<Platform[]>("/platforms"),
    apiGet<SalesMarket[]>("/sales-markets"),
    apiGet<Product[]>("/products"),
  ]);

  const [statuses, publicationsNested] = await Promise.all([
    Promise.all(platforms.map((platform) => apiGet<PlatformConnectorStatus>(`/platforms/${platform.id}/connector-status`))),
    Promise.all(products.map((product) => apiGet<ProductPublication[]>(`/products/${product.id}/publications`))),
  ]);

  return {
    platforms,
    markets,
    statuses: statuses.filter((status): status is PlatformConnectorStatus => Boolean(status)),
    products,
    publications: publicationsNested.flat(),
  };
}

export async function getSalesChannelDetailData(platformId: number): Promise<SalesChannelDetailData> {
  const [platforms, status, credentials, products] = await Promise.all([
    apiGet<Platform[]>("/platforms"),
    apiGet<PlatformConnectorStatus>(`/platforms/${platformId}/connector-status`),
    apiGet<PlatformCredential[]>(`/platforms/${platformId}/credentials`),
    apiGet<Product[]>("/products"),
  ]);

  const platform = platforms.find((item) => item.id === platformId);
  if (!platform) {
    throw new Error(`Verkoopkanaal ${platformId} niet gevonden`);
  }

  const publicationsNested = await Promise.all(
    products.map((product) => apiGet<ProductPublication[]>(`/products/${product.id}/publications`)),
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
  return apiGet<AIProductStatus>("/ai/product-draft/status");
}

export async function getSystemReadiness(): Promise<SystemReadiness> {
  return apiGet<SystemReadiness>("/system/readiness");
}
