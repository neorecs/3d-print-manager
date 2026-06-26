export type Platform = {
  id: number;
  name: string;
  type: string;
  api_base_url?: string | null;
  active: boolean;
};

export type Product = {
  id: number;
  name: string;
  internal_title?: string | null;
  short_description?: string | null;
  long_description?: string | null;
  sales_description?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  internal_category?: string | null;
  product_type?: string | null;
  status?: string | null;
  active?: boolean;
};

export type ProductVariant = {
  id: number;
  product_id: number;
  variant_name?: string | null;
  sku?: string | null;
  color?: string | null;
  material?: string | null;
  size?: string | null;
  finish?: string | null;
  print_file_path?: string | null;
  estimated_print_time_minutes?: number | null;
  estimated_filament_grams?: number | null;
  weight_grams?: number | null;
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  default_sale_price?: number | null;
  action_sale_price?: number | null;
  cost_price?: number | null;
  active?: boolean;
};

export type ProductMedia = {
  id: number;
  product_id: number;
  file_path?: string | null;
  media_type?: string | null;
  alt_text?: string | null;
  sort_order?: number | null;
  is_primary?: boolean | null;
};

export type ProductTag = {
  id: number;
  product_id: number;
  tag: string;
};

export type Order = {
  id: number;
  internal_order_number: string;
  platform_id: number;
  external_order_id?: string | null;
  customer_name?: string | null;
  customer_email?: string | null;
  order_date?: string | null;
  total_amount?: number | null;
  currency?: string | null;
  status?: string | null;
};

export type OrderItem = {
  id: number;
  order_id: number;
  product_id?: number | null;
  product_variant_id?: number | null;
  external_order_item_id?: string | null;
  sku?: string | null;
  quantity_ordered: number;
  quantity_from_inventory: number;
  quantity_to_print: number;
  unit_sale_price?: number | null;
  inventory_status?: string | null;
  print_job_id?: number | null;
};

export type OrderDetail = Order & {
  items: OrderItem[];
};

export type ProductInventory = {
  id: number;
  product_id: number;
  product_variant_id: number;
  color?: string | null;
  material?: string | null;
  quantity_on_hand: number;
  quantity_reserved: number;
  minimum_stock_level: number;
  location?: string | null;
};

export type FilamentSpool = {
  id: number;
  brand: string;
  material: string;
  color: string;
  initial_weight_grams: number;
  remaining_weight_grams: number;
  purchase_price: number;
  price_per_gram?: number | null;
  minimum_remaining_grams: number;
  location?: string | null;
  active: boolean;
};

export type FilamentData = {
  filament: FilamentSpool[];
  printJobs: PrintJob[];
};

export type PrintJob = {
  id: number;
  order_item_id?: number | null;
  product_id: number;
  product_variant_id: number;
  color?: string | null;
  material?: string | null;
  quantity_needed: number;
  quantity_planned: number;
  quantity_succeeded?: number | null;
  quantity_failed?: number | null;
  quantity_to_order?: number | null;
  quantity_to_inventory?: number | null;
  estimated_print_time_minutes?: number | null;
  estimated_filament_grams?: number | null;
  status?: string | null;
  planned_date?: string | null;
};

export type PrintBatch = {
  id: number;
  batch_name: string;
  planned_date?: string | null;
  material?: string | null;
  color?: string | null;
  estimated_total_print_time_minutes?: number | null;
  estimated_total_filament_grams?: number | null;
  status?: string | null;
};

export type PrintBatchItem = {
  id: number;
  print_batch_id: number;
  print_job_id: number;
  quantity_in_batch: number;
};

export type StockRecommendation = {
  id: number;
  product_id: number;
  product_variant_id: number;
  product?: string | null;
  variant?: string | null;
  sku?: string | null;
  color?: string | null;
  material?: string | null;
  current_free_stock: number;
  expected_sales: number;
  safety_stock?: number | null;
  recommended_stock_level?: number | null;
  recommended_print_quantity: number;
  reason?: string | null;
  status?: string | null;
};

export type ProductPublication = {
  id: number;
  product_id: number;
  platform_id: number;
  external_product_id?: string | null;
  external_listing_id?: string | null;
  publication_status?: string | null;
  platform_title?: string | null;
  platform_description?: string | null;
  platform_category?: string | null;
  platform_tags?: string | null;
  platform_price_override?: number | null;
  platform_shipping_profile_id?: string | null;
  last_synced_at?: string | null;
  last_error?: string | null;
};

export type DashboardData = {
  products: Product[];
  platforms: Platform[];
  orders: Order[];
  inventory: ProductInventory[];
  filament: FilamentSpool[];
  printJobs: PrintJob[];
  recommendations: StockRecommendation[];
  publications: ProductPublication[];
};

export type OrdersData = {
  orders: Order[];
  orderItems: OrderItem[];
  platforms: Platform[];
  products: Product[];
  variants: ProductVariant[];
  printJobs: PrintJob[];
};

export type OrderDetailData = {
  order: OrderDetail;
  platform?: Platform | null;
  products: Product[];
  variants: ProductVariant[];
  printJobs: PrintJob[];
};

export type PrintPlanningData = {
  printJobs: PrintJob[];
  printBatches: PrintBatch[];
  products: Product[];
  variants: ProductVariant[];
  orders: Order[];
  orderItems: OrderItem[];
};

export type ProductCatalogRow = {
  product: Product;
  variants: ProductVariant[];
  inventory: ProductInventory[];
  publications: ProductPublication[];
};

export type ProductCatalogData = {
  products: Product[];
  variants: ProductVariant[];
  inventory: ProductInventory[];
  platforms: Platform[];
  rows: ProductCatalogRow[];
};

export type ProductDetailData = {
  product: Product;
  variants: ProductVariant[];
  inventory: ProductInventory[];
  media: ProductMedia[];
  tags: ProductTag[];
  publications: ProductPublication[];
  platforms: Platform[];
};

export type PlatformConnectorStatus = {
  platform_id: number;
  platform: string;
  platform_type: string;
  mode: string;
  required_credentials: string[];
  configured_credentials: string[];
  missing_credentials: string[];
  ready_for_live: boolean;
};

export type InventoryMovement = {
  id: number;
  product_inventory_id: number;
  movement_type: string;
  quantity: number;
  order_id?: number | null;
  order_item_id?: number | null;
  print_job_id?: number | null;
  note?: string | null;
  quantity_on_hand_before?: number | null;
  quantity_on_hand_after?: number | null;
  quantity_reserved_before?: number | null;
  quantity_reserved_after?: number | null;
  free_stock_before?: number | null;
  free_stock_after?: number | null;
  source?: string | null;
  reason?: string | null;
  performed_by?: string | null;
  created_at?: string | null;
};

export type AnalyticsRow = {
  product_id?: number;
  product_variant_id?: number;
  product?: string;
  variant?: string;
  color?: string;
  material?: string;
  period_days?: number;
  quantity_sold: number;
  average_weekly_sales?: number;
  revenue: number;
  estimated_profit: number;
};

export type CostSetting = {
  id: number;
  setting_name: string;
  value: number;
};

export type AIProductStatus = {
  enabled: boolean;
  configured: boolean;
  model: string;
  ready: boolean;
  note: string;
};

export type InventoryData = {
  inventory: ProductInventory[];
  movements: InventoryMovement[];
  products: Product[];
  variants: ProductVariant[];
};

export type SalesChannelsData = {
  platforms: Platform[];
  statuses: PlatformConnectorStatus[];
  products: Product[];
  publications: ProductPublication[];
};

export type AnalyticsData = {
  salesTrends: AnalyticsRow[];
  topProducts: AnalyticsRow[];
  topColors: AnalyticsRow[];
  topMaterials: AnalyticsRow[];
  recommendations: StockRecommendation[];
  costSettings: CostSetting[];
};
