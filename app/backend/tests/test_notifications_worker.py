from unittest.mock import patch

from support import *

from models import Notification
from services import notification_service
from services.notification_service import NotificationError, notify, notify_new_order, retry_failed_notifications

TELEGRAM_ENV = {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "42", "APP_PUBLIC_URL": "http://nas.local:38502"}

PAID_ORDER = {
    "external_order_id": "r-1", "order_number": "r-1", "external_status": "paid", "payment_status": "betaald",
    "total_amount": 38.9, "currency": "EUR",
    "items": [{"external_order_item_id": "t-1", "sku": "TEST-SKU", "quantity_ordered": 2, "unit_sale_price": 19.45}],
}


class NotificationTests(BackendTestCase):
    def test_no_channels_means_nothing_is_sent(self) -> None:
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "", "NTFY_URL": ""}):
            self.assertEqual(notify(self.db, "x", "order", "1", "Titel", "Tekst"), [])

    def test_event_is_sent_once_per_channel(self) -> None:
        sent = []
        with patch.dict(os.environ, {**TELEGRAM_ENV, "NTFY_URL": "https://ntfy.sh/mijn-topic"}), \
                patch.dict(notification_service.SENDERS, {"telegram": lambda *a: sent.append("telegram"), "ntfy": lambda *a: sent.append("ntfy")}):
            first = notify(self.db, "order.created", "order", "1", "Nieuwe order", "Tekst")
            second = notify(self.db, "order.created", "order", "1", "Nieuwe order", "Tekst")

        self.assertEqual(sorted(sent), ["ntfy", "telegram"])
        self.assertEqual(len(first), 2)
        self.assertEqual(second, [])
        self.assertTrue(all(item.status == "verstuurd" for item in first))

    def test_failed_send_is_retried_up_to_three_attempts(self) -> None:
        def failing(*args):
            raise NotificationError("geen verbinding")

        with patch.dict(os.environ, TELEGRAM_ENV), patch.dict(notification_service.SENDERS, {"telegram": failing}):
            [notification] = notify(self.db, "order.created", "order", "1", "Nieuwe order", "Tekst")
            self.assertEqual(notification.status, "mislukt")
            retry_failed_notifications(self.db)
            retry_failed_notifications(self.db)
            self.assertEqual(retry_failed_notifications(self.db), 0)

        self.assertEqual(notification.attempts, 3)
        self.assertEqual(notification.last_error, "geen verbinding")

    def test_new_order_message_lists_products_amount_and_link(self) -> None:
        platform = self.make_platform("etsy")
        self.make_product_variant()
        from services.order_import_service import upsert_imported_order
        imported = upsert_imported_order(self.db, platform, PAID_ORDER)
        self.db.commit()
        order = self.db.get(Order, imported["order"]["id"])
        captured = []

        with patch.dict(os.environ, TELEGRAM_ENV), patch.dict(notification_service.SENDERS, {"telegram": lambda *a: captured.append(a)}):
            notify_new_order(self.db, order)

        title, body, link = captured[0]
        self.assertEqual(title, "Nieuwe order via Etsy")
        self.assertIn("2× Test product", body)
        self.assertIn("€ 38,90", body)
        self.assertEqual(link, f"http://nas.local:38502/orders/{order.id}")


class WorkerTests(BackendTestCase):
    def test_worker_imports_new_orders_and_notifies_once(self) -> None:
        import worker

        platform = self.make_platform("etsy")
        self.make_product_variant()
        sent = []
        with patch.dict(os.environ, {**TELEGRAM_ENV, "CONNECTORS_LIVE_MODE": "true", "WORKER_STATUS_DIR": ""}), \
                patch.object(EtsyConnector, "import_orders", lambda self_connector, **kwargs: {"success": True, "orders": [PAID_ORDER]}), \
                patch.dict(notification_service.SENDERS, {"telegram": lambda *a: sent.append(a[0])}):
            first = worker.run_once(self.db)
            second = worker.run_once(self.db)

        self.assertEqual(first["new_orders"], 1)
        self.assertEqual(second["new_orders"], 0)
        self.assertEqual(sent, ["Nieuwe order via Etsy"])
        self.assertEqual(len(self.db.scalars(select(Notification)).all()), 1)

    def test_worker_can_process_new_orders_automatically(self) -> None:
        import worker

        platform = self.make_platform("etsy")
        product, variant = self.make_product_variant()
        self.db.add(ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=5, quantity_reserved=0))
        self.db.commit()
        with patch.dict(os.environ, {"CONNECTORS_LIVE_MODE": "true", "WORKER_AUTO_PROCESS_ORDERS": "true", "TELEGRAM_BOT_TOKEN": "", "NTFY_URL": "", "WORKER_STATUS_DIR": ""}), \
                patch.object(EtsyConnector, "import_orders", lambda self_connector, **kwargs: {"success": True, "orders": [PAID_ORDER]}):
            worker.run_once(self.db)

        inventory = self.db.scalar(select(ProductInventory))
        self.assertEqual(inventory.quantity_reserved, 2)

    def test_worker_skips_imports_when_live_mode_is_off(self) -> None:
        import worker

        self.make_platform("etsy")
        with patch.dict(os.environ, {"CONNECTORS_LIVE_MODE": "false", "WORKER_STATUS_DIR": ""}), \
                patch.object(EtsyConnector, "import_orders", side_effect=AssertionError("should not import")):
            report = worker.run_once(self.db)
        self.assertEqual(report["imported_platforms"], 0)

    def test_failed_import_sends_one_warning_per_day(self) -> None:
        import worker

        self.make_platform("etsy")
        sent = []
        with patch.dict(os.environ, {**TELEGRAM_ENV, "CONNECTORS_LIVE_MODE": "true", "WORKER_STATUS_DIR": ""}), \
                patch.object(EtsyConnector, "import_orders", lambda self_connector, **kwargs: {"success": False, "message": "Etsy HTTP 401"}), \
                patch.dict(notification_service.SENDERS, {"telegram": lambda *a: sent.append(a[0])}):
            worker.run_once(self.db)
            worker.run_once(self.db)

        self.assertEqual(sent, ["Orderimport Etsy mislukt"])
