from datetime import date, datetime, timezone
from decimal import Decimal

from support import *

from domain.statuses import ACCOUNTING_CLOSED
from models import AccountingFiscalSetting, AccountingSale, Order, VatPeriod
from services.accounting_service import (
    accounting_vat_summary_data,
    create_accounting_sale_from_order,
    ensure_accounting_date_open,
    fill_vat_amounts,
)


class AccountingTestCase(BackendTestCase):
    def test_vat_calculation_rounds_money_to_cents(self) -> None:
        values = fill_vat_amounts({"net_amount": "0.10", "vat_rate": "21", "vat_amount": None, "gross_amount": None})

        self.assertEqual(values["net_amount"], Decimal("0.10"))
        self.assertEqual(values["vat_amount"], Decimal("0.02"))
        self.assertEqual(values["gross_amount"], Decimal("0.12"))

    def test_closed_vat_period_blocks_new_bookings(self) -> None:
        self.db.add(VatPeriod(
            period_name="2026-Q1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status=ACCOUNTING_CLOSED,
        ))
        self.db.commit()

        with self.assertRaises(HTTPException) as error:
            ensure_accounting_date_open(self.db, date(2026, 2, 1))

        self.assertEqual(error.exception.status_code, 409)

    def test_order_booking_uses_configured_vat_rate_and_is_idempotent(self) -> None:
        platform = self.make_platform()
        order = Order(
            internal_order_number="ACC-001",
            platform_id=platform.id,
            external_order_id="ACC-EXT-001",
            order_date=datetime(2026, 4, 2, tzinfo=timezone.utc),
            total_amount=Decimal("121.00"),
            currency="EUR",
        )
        self.db.add_all([order, AccountingFiscalSetting(setting_name="default_vat_rate", value="21")])
        self.db.commit()

        first = create_accounting_sale_from_order(self.db, order)
        second = create_accounting_sale_from_order(self.db, order)

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        sale = self.db.scalar(select(AccountingSale).where(AccountingSale.order_id == order.id))
        self.assertEqual(Decimal(sale.net_amount), Decimal("100.00"))
        self.assertEqual(Decimal(sale.vat_amount), Decimal("21.00"))
        self.assertEqual(accounting_vat_summary_data(self.db)["vat_due"], 21.0)
