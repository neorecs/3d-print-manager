from pydantic import BaseModel


class PlatformCreate(BaseModel):
    name: str
    type: str
    api_base_url: str | None = None
    active: bool = True


class AuthLogin(BaseModel):
    email: str
    password: str


class AuthBootstrapAdmin(BaseModel):
    bootstrap_secret: str
    email: str
    password: str
    display_name: str | None = "Beheerder"


class AuthMfaSetup(BaseModel):
    email: str
    password: str


class AuthMfaConfirm(BaseModel):
    email: str
    password: str
    code: str


class PlatformCredentialCreate(BaseModel):
    key_name: str
    encrypted_value: str


class SalesMarketCreate(BaseModel):
    country_code: str
    country_name: str
    primary_language: str = "nl"
    additional_languages: str | None = None
    currency: str = "EUR"
    active: bool = True
    note: str | None = None


class BambuPrinterCreate(BaseModel):
    name: str
    model: str | None = None
    serial_number: str | None = None
    host: str
    mqtt_port: int = 8883
    access_code: str | None = None
    connection_mode: str = "lan"
    location: str | None = None
    active: bool = True


class AccountingSaleCreate(BaseModel):
    order_id: int | None = None
    platform_id: int | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    customer_name: str | None = None
    customer_country: str | None = None
    description: str | None = None
    net_amount: float = 0
    vat_rate: float = 21
    vat_amount: float | None = None
    gross_amount: float | None = None
    currency: str = "EUR"
    status: str = "concept"
    source: str = "manual"
    note: str | None = None


class AccountingPurchaseCreate(BaseModel):
    supplier_name: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    category: str = "overig"
    description: str | None = None
    net_amount: float = 0
    vat_rate: float = 21
    vat_amount: float | None = None
    gross_amount: float | None = None
    currency: str = "EUR"
    payment_status: str = "onbekend"
    source: str = "manual"
    note: str | None = None


class AccountingCorrectionCreate(BaseModel):
    reason: str
    correction_date: str | None = None


class VatPeriodCloseCreate(BaseModel):
    period_name: str
    start_date: str
    end_date: str
    note: str | None = None


class AccountingFiscalSettingCreate(BaseModel):
    setting_name: str
    value: str
    note: str | None = None


class ProductCreate(BaseModel):
    name: str
    internal_title: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    sales_description: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    product_type: str | None = None
    internal_category: str | None = None
    status: str = "concept"
    active: bool = True


class AIProductDraftRequest(BaseModel):
    idea: str
    audience: str | None = None
    style: str | None = None
    material: str | None = None
    colors: str | None = None
    product_type: str | None = None
    category: str | None = None
    price: float | None = None
    print_time: int | None = None
    filament: float | None = None
    dimensions: str | None = None
    keywords: str | None = None
    platforms: list[str] = []


class ProductTranslationCreate(BaseModel):
    language_code: str
    title: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    sales_description: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    tags: str | None = None
    source: str = "manual"
    status: str = "concept"


class ProductTranslationGenerate(BaseModel):
    language_codes: list[str] = ["de"]
    overwrite: bool = False


class ProductVariantCreate(BaseModel):
    product_id: int
    variant_name: str
    sku: str
    color: str | None = None
    material: str | None = None
    size: str | None = None
    finish: str | None = None
    print_file_path: str | None = None
    estimated_print_time_minutes: int | None = None
    estimated_filament_grams: float | None = None
    weight_grams: float | None = None
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    default_sale_price: float | None = None
    action_sale_price: float | None = None
    cost_price: float | None = None
    active: bool = True


class ProductMediaCreate(BaseModel):
    file_path: str
    media_type: str = "image"
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False


class ProductTagCreate(BaseModel):
    tag: str


class ProductPlatformPublicationCreate(BaseModel):
    platform_id: int
    external_product_id: str | None = None
    external_listing_id: str | None = None
    publication_status: str = "niet_gepubliceerd"
    platform_title: str | None = None
    platform_description: str | None = None
    platform_category: str | None = None
    platform_tags: str | None = None
    platform_price_override: float | None = None
    platform_shipping_profile_id: str | None = None
    last_synced_at: str | None = None
    last_error: str | None = None


class ProductPublicationMediaItemCreate(BaseModel):
    product_media_id: int
    sort_order: int = 0
    active: bool = True


class ProductPublicationMediaBulkUpdate(BaseModel):
    items: list[ProductPublicationMediaItemCreate] = []


class ProductInventoryCreate(BaseModel):
    product_id: int
    product_variant_id: int
    color: str | None = None
    material: str | None = None
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    minimum_stock_level: int = 0
    location: str | None = None


class OrderCreate(BaseModel):
    internal_order_number: str
    platform_id: int
    external_order_id: str
    customer_name: str | None = None
    customer_email: str | None = None
    order_date: str | None = None
    total_amount: float | None = None
    currency: str = "EUR"
    status: str = "nieuw"


class OrderItemCreate(BaseModel):
    order_id: int
    product_id: int | None = None
    product_variant_id: int | None = None
    external_order_item_id: str | None = None
    sku: str | None = None
    quantity_ordered: int
    quantity_from_inventory: int = 0
    quantity_to_print: int = 0
    unit_sale_price: float | None = None
    inventory_status: str = "niet_op_voorraad"
    print_job_id: int | None = None


class FilamentSpoolCreate(BaseModel):
    brand: str
    material: str
    color: str
    initial_weight_grams: float
    remaining_weight_grams: float
    purchase_price: float
    minimum_remaining_grams: float = 100
    location: str | None = None
    active: bool = True


class PrintJobCreate(BaseModel):
    order_item_id: int | None = None
    product_id: int
    product_variant_id: int
    color: str | None = None
    material: str | None = None
    quantity_needed: int = 0
    quantity_planned: int = 0
    quantity_succeeded: int = 0
    quantity_failed: int = 0
    quantity_to_order: int = 0
    quantity_to_inventory: int = 0
    estimated_print_time_minutes: int | None = None
    estimated_filament_grams: int | None = None
    status: str = "nieuw"


class PrintJobComplete(BaseModel):
    quantity_succeeded: int
    quantity_failed: int = 0
    quantity_to_order: int | None = None


class PrintBatchCreate(BaseModel):
    batch_name: str
    planned_date: str | None = None
    material: str | None = None
    color: str | None = None
    print_job_ids: list[int] = []


class CostSettingCreate(BaseModel):
    setting_name: str
    value: float = 0


class StockRecommendationGenerate(BaseModel):
    period_days: int = 30
    safety_stock: int = 2
    weeks_ahead: int = 1


class StockRecommendationUpdate(BaseModel):
    safety_stock: int
    recommended_print_quantity: int
    reason: str | None = None
