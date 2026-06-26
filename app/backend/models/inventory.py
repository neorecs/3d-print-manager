from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class ProductInventory(TimestampMixin, Base):
    __tablename__ = "product_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    color: Mapped[str | None] = mapped_column(String(80))
    material: Mapped[str | None] = mapped_column(String(80))
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))

    @property
    def free_stock(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_inventory_id: Mapped[int] = mapped_column(ForeignKey("product_inventory.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"))
    print_job_id: Mapped[int | None] = mapped_column(ForeignKey("print_jobs.id"))
    note: Mapped[str | None] = mapped_column(Text)
    quantity_on_hand_before: Mapped[int | None] = mapped_column(Integer)
    quantity_on_hand_after: Mapped[int | None] = mapped_column(Integer)
    quantity_reserved_before: Mapped[int | None] = mapped_column(Integer)
    quantity_reserved_after: Mapped[int | None] = mapped_column(Integer)
    free_stock_before: Mapped[int | None] = mapped_column(Integer)
    free_stock_after: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[str | None] = mapped_column(String(120))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FilamentSpool(TimestampMixin, Base):
    __tablename__ = "filament_spools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    material: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(80), nullable=False)
    initial_weight_grams: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_weight_grams: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_gram: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    minimum_remaining_grams: Mapped[float] = mapped_column(Numeric(10, 2), default=100, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
