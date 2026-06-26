export type Platform = {
  id: number;
  name: string;
  type: string;
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
  remaining_weight_grams: number;
  minimum_remaining_grams: number;
  active: boolean;
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
  current_free_stock: number;
  expected_sales: number;
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
