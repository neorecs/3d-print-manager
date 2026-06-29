import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("CONNECTORS_LIVE_MODE", "false")

from api.routes import (  # noqa: E402
    complete_print_job,
    convert_stock_recommendation,
    generate_stock_recommendations,
    process_order_inventory,
    publish_product_publication,
    suggest_print_batches,
    update_stock_recommendation,
    validate_publication_record,
)
from core.credentials import decrypt_credential, encrypt_credential, is_encrypted_credential  # noqa: E402
from connectors.shopify.connector import ShopifyConnector  # noqa: E402
from connectors.etsy.connector import EtsyConnector  # noqa: E402
from database import Base  # noqa: E402
from inventory.service import adjust_product_inventory as adjust_inventory_service  # noqa: E402
from services.ai_product_assistant import generate_product_translation  # noqa: E402
from models import (  # noqa: E402
    InventoryMovement,
    Order,
    OrderItem,
    Platform,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductTranslation,
    ProductVariantPlatformLink,
    ProductVariant,
    SalesMarket,
    StockRecommendation,
)
from schemas.common import PrintJobComplete, StockRecommendationGenerate, StockRecommendationUpdate  # noqa: E402


class BackendTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def make_platform(self, platform_type: str = "etsy") -> Platform:
        platform = Platform(name=platform_type.title(), type=platform_type, active=True)
        self.db.add(platform)
        self.db.commit()
        self.db.refresh(platform)
        return platform

    def make_product_variant(self, sku: str = "TEST-SKU") -> tuple[Product, ProductVariant]:
        product = Product(
            name="Test product",
            internal_title="Test product",
            short_description="Korte omschrijving",
            long_description="Lange omschrijving",
            sales_description="Verkooptekst",
            seo_title="SEO titel",
            seo_description="SEO omschrijving",
            product_type="decoratie",
            internal_category="test",
            status="klaar_voor_publicatie",
            active=True,
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        variant = ProductVariant(
            product_id=product.id,
            variant_name="Rood PLA",
            sku=sku,
            color="rood",
            material="PLA",
            print_file_path="prints/test.3mf",
            estimated_print_time_minutes=45,
            estimated_filament_grams=32,
            default_sale_price=12.95,
            cost_price=2.50,
            active=True,
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return product, variant
