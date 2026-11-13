from decimal import Decimal

from support import *

from api.routes.planning import estimate_item_profit
from models import AccountingSale
from services.accounting_service import calculate_order_profit, net_from_gross


class OrderProfitTests(BackendTestCase):
    def make_order(self, unit_price: float):
        platform = self.make_platform()
        product, variant = self.make_product_variant()
        variant.estimated_filament_grams = 30
        variant.estimated_print_time_minutes = 60
        order = Order(internal_order_number="PROFIT-1", external_order_id="PROFIT-1", platform_id=platform.id, status="nieuw")
        self.db.add(order)
        self.db.flush()
        item = OrderItem(order_id=order.id, product_id=product.id, product_variant_id=variant.id, sku=variant.sku,
                         quantity_ordered=1, unit_sale_price=unit_price)
        self.db.add(item)
        self.db.commit()
        return platform, order, item, variant

    def test_net_from_gross_removes_vat(self) -> None:
        self.assertEqual(net_from_gross(Decimal("24.95"), Decimal("21")), Decimal("20.62"))
        self.assertEqual(net_from_gross(Decimal("10.90"), Decimal("9")), Decimal("10.00"))
        self.assertEqual(net_from_gross(Decimal("5.00"), Decimal("0")), Decimal("5.00"))

    def test_profit_excludes_vat_and_charges_fees_on_gross_price(self) -> None:
        _, order, _, _ = self.make_order(24.95)

        calculation = calculate_order_profit(self.db, order.id)

        # Net 20.62; filament 30 g x 0.02 = 0.60; packaging 0.75;
        # platform fee 6.5% of 24.95 + 0.30 = 1.92; electricity 1 h x 0.35 = 0.35.
        self.assertEqual(Decimal(str(calculation.sale_amount)), Decimal("20.62"))
        self.assertEqual(Decimal(str(calculation.platform_fee)), Decimal("1.92"))
        self.assertEqual(Decimal(str(calculation.filament_cost)), Decimal("0.60"))
        self.assertEqual(Decimal(str(calculation.electricity_cost)), Decimal("0.35"))
        self.assertEqual(Decimal(str(calculation.estimated_profit)), Decimal("17.00"))

    def test_profit_uses_vat_rate_booked_for_the_order(self) -> None:
        platform, order, _, _ = self.make_order(10.90)
        self.db.add(AccountingSale(order_id=order.id, platform_id=platform.id, invoice_number="PROFIT-1",
                                   net_amount=10, vat_rate=9, vat_amount=0.9, gross_amount=10.9, status="concept"))
        self.db.commit()

        calculation = calculate_order_profit(self.db, order.id)

        self.assertEqual(Decimal(str(calculation.sale_amount)), Decimal("10.00"))

    def test_sales_analysis_profit_excludes_vat(self) -> None:
        _, _, item, variant = self.make_order(24.95)

        profit = estimate_item_profit(self.db, item, variant, 24.95)

        # 20.62 net - 0.60 filament - 2.50 variant cost price
        self.assertAlmostEqual(profit, 17.52, places=2)
