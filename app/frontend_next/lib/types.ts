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
  internal_category?: string | null;
  product_type?: string | null;
  status?: string | null;
  active?: boolean;
};

export type Order = {
  id: number;
  internal_order_number: string;
  platform_id: number;
  customer_name?: string | null;
  order_date?: string | null;
  total_amount?: number | null;
  status?: string | null;
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
  product_id: number;
  product_variant_id: number;
  color?: string | null;
  material?: string | null;
  quantity_needed: number;
  quantity_planned: number;
  estimated_print_time_minutes?: number | null;
  status?: string | null;
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
  publication_status?: string | null;
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
