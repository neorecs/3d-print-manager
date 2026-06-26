from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_order_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(180))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    order_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="nieuw", nullable=False)


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    external_order_item_id: Mapped[str | None] = mapped_column(String(255))
    sku: Mapped[str | None] = mapped_column(String(120))
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_from_inventory: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_to_print: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    inventory_status: Mapped[str] = mapped_column(String(80), default="niet_op_voorraad", nullable=False)
    print_job_id: Mapped[int | None] = mapped_column(ForeignKey("print_jobs.id"))
