import base64
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


@unittest.skipUnless(POSTGRES_URL, "Alleen uitvoeren met de tijdelijke PostgreSQL-testdatabase")
class PostgreSQLOrderIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from database import Base, SessionLocal, engine
        from main import app

        cls.Base = Base
        cls.SessionLocal = SessionLocal
        cls.engine = engine
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.engine.dispose()

    def setUp(self):
        from models import User

        table_names = ", ".join(f'"{table.name}"' for table in self.Base.metadata.sorted_tables)
        with self.engine.begin() as connection:
            connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        with self.SessionLocal() as db:
            user = User(
                email="postgres-test@example.invalid",
                display_name="PostgreSQL test",
                password_hash="not-used-in-this-test",
                role="admin",
                is_active=True,
                must_change_password=False,
                session_version=1,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            payload = {
                "userId": user.id,
                "sessionVersion": user.session_version,
                "email": user.email,
                "name": user.display_name,
                "role": user.role,
                "mustChangePassword": False,
                "exp": int(time.time()) + 300,
            }
        body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(
            hmac.new(os.environ["AUTH_SECRET"].encode(), body.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        self.headers = {
            "X-Backend-Internal-Token": os.environ["BACKEND_INTERNAL_TOKEN"],
            "X-Session-Token": f"{body}.{signature}",
        }

    def make_orders(self, quantities, stock=6):
        from models import Order, OrderItem, Platform, Product, ProductInventory, ProductVariant

        with self.SessionLocal() as db:
            platform = Platform(name="Test", type="etsy", active=True)
            product = Product(name="Test product", internal_title="Test product", status="concept", active=True)
            db.add_all([platform, product])
            db.flush()
            variant = ProductVariant(
                product_id=product.id,
                variant_name="Rood PLA",
                sku="PG-CONCURRENCY-SKU",
                color="rood",
                material="PLA",
                estimated_print_time_minutes=10,
                estimated_filament_grams=5,
                default_sale_price=12.95,
                active=True,
            )
            db.add(variant)
            db.flush()
            inventory = ProductInventory(
                product_id=product.id,
                product_variant_id=variant.id,
                quantity_on_hand=stock,
                quantity_reserved=0,
            )
            db.add(inventory)
            order_ids = []
            for index, quantity in enumerate(quantities, start=1):
                order = Order(
                    internal_order_number=f"PG-{index}",
                    external_order_id=f"PG-{index}",
                    platform_id=platform.id,
                    total_amount=quantity * 12.95,
                    status="nieuw",
                )
                db.add(order)
                db.flush()
                db.add(OrderItem(order_id=order.id, sku=variant.sku, quantity_ordered=quantity, unit_sale_price=12.95))
                order_ids.append(order.id)
            db.commit()
            return order_ids, inventory.id

    def process_concurrently(self, order_ids):
        barrier = threading.Barrier(len(order_ids))

        def process(order_id):
            barrier.wait(timeout=10)
            response = self.client.post(f"/orders/{order_id}/process", headers=self.headers)
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=len(order_ids)) as executor:
            return list(executor.map(process, order_ids))

    def test_same_order_is_idempotent_under_concurrent_api_requests(self):
        from sqlalchemy import func, select
        from models import AccountingSale, InventoryMovement, PrintJob, ProductInventory

        order_ids, inventory_id = self.make_orders([10])
        results = self.process_concurrently([order_ids[0], order_ids[0]])
        self.assertEqual([status for status, _ in results], [200, 200])
        with self.SessionLocal() as db:
            inventory = db.get(ProductInventory, inventory_id)
            self.assertEqual(inventory.quantity_reserved, 6)
            self.assertEqual(db.scalar(select(func.count(PrintJob.id))), 1)
            self.assertEqual(db.scalar(select(func.count(AccountingSale.id))), 1)
            self.assertEqual(db.scalar(select(func.count(InventoryMovement.id))), 1)

    def test_two_orders_cannot_reserve_more_than_available_stock(self):
        from sqlalchemy import func, select
        from models import AccountingSale, OrderItem, PrintJob, ProductInventory

        order_ids, inventory_id = self.make_orders([4, 4])
        results = self.process_concurrently(order_ids)
        self.assertEqual([status for status, _ in results], [200, 200])
        with self.SessionLocal() as db:
            inventory = db.get(ProductInventory, inventory_id)
            items = db.scalars(select(OrderItem).order_by(OrderItem.id)).all()
            self.assertEqual(inventory.quantity_reserved, 6)
            self.assertEqual(sum(item.quantity_from_inventory for item in items), 6)
            self.assertEqual(sum(item.quantity_to_print for item in items), 2)
            self.assertEqual(db.scalar(select(func.count(PrintJob.id))), 1)
            self.assertEqual(db.scalar(select(func.count(AccountingSale.id))), 2)
