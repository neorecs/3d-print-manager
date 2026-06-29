import csv
import io
import re
import shutil
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import list_rows, to_dict
from connectors.factory import get_platform_connector
from core.config import get_settings
from core.credentials import encrypt_credential, generate_credential_key, is_encrypted_credential
from database import get_db
from models import (
    AccountingDocument,
    AccountingFiscalSetting,
    AccountingPurchase,
    AccountingSale,
    BambuPrinter,
    CostSetting,
    FilamentSpool,
    InventoryMovement,
    Order,
    OrderItem,
    OrderProfitCalculation,
    Platform,
    PlatformCredential,
    PlatformImportLog,
    PrintBatch,
    PrintBatchItem,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductPublicationMedia,
    ProductTag,
    ProductTranslation,
    ProductVariant,
    ProductVariantPlatformLink,
    SalesMarket,
    StockRecommendation,
    TrendSnapshot,
    VatPeriod,
)
from schemas.common import (
    AccountingPurchaseCreate,
    AccountingCorrectionCreate,
    AccountingFiscalSettingCreate,
    AccountingSaleCreate,
    VatPeriodCloseCreate,
    BambuPrinterCreate,
    CostSettingCreate,
    AIProductDraftRequest,
    FilamentSpoolCreate,
    OrderCreate,
    OrderItemCreate,
    PlatformCreate,
    PlatformCredentialCreate,
    PrintBatchCreate,
    PrintJobComplete,
    PrintJobCreate,
    ProductCreate,
    ProductInventoryCreate,
    ProductMediaCreate,
    ProductPlatformPublicationCreate,
    ProductPublicationMediaBulkUpdate,
    ProductTranslationCreate,
    ProductTranslationGenerate,
    ProductTagCreate,
    ProductVariantCreate,
    SalesMarketCreate,
    StockRecommendationGenerate,
    StockRecommendationUpdate,
)
from services.accounting_service import (
    accounting_purchases_query,
    accounting_sales_query,
    accounting_vat_summary_data,
    calculate_order_gross_amount,
    calculate_order_profit,
    create_accounting_sale_from_order,
    csv_download,
    fill_vat_amounts,
    get_filament_price_per_gram,
    parse_date_range,
    parse_optional_date,
    seed_default_cost_settings,
    seed_default_fiscal_settings,
)
from services.ai_product_assistant import generate_ai_product_draft, generate_product_translation
from services.bambu_printers import public_bambu_printer_dict, refresh_bambu_mqtt_status, test_bambu_lan_connection
from services.platform_service import public_credential_dict
from publishing.service import (
    mark_product_publications_sync_needed,
    publish_publication,
    sync_publication,
    validate_publication_record,
)
from inventory.service import (
    add_inventory_movement,
    adjust_product_inventory as adjust_inventory_stock,
    inventory_snapshot,
    link_order_item_by_sku,
    list_product_inventory_rows,
    process_order_inventory as process_order_inventory_service,
    release_product_inventory as release_inventory_stock,
    reserve_product_inventory as reserve_inventory_stock,
)
from services.dummy_data import seed_dummy_data

# Routers live in api/routes/*.py after the phase 1 split.

UPLOAD_ROOT = Path("uploads/product_media")
ACCOUNTING_UPLOAD_ROOT = Path("uploads/accounting_documents")
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_ACCOUNTING_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def get_or_404(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return item


