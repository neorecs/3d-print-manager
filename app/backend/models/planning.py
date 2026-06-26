from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class PrintJob(TimestampMixin, Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    color: Mapped[str | None] = mapped_column(String(80))
    material: Mapped[str | None] = mapped_column(String(80))
    quantity_needed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_planned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_to_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_to_inventory: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_print_time_minutes: Mapped[int | None] = mapped_column(Integer)
    estimated_filament_grams: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(80), default="nieuw", nullable=False)
    planned_date: Mapped[date | None] = mapped_column(Date)


class PrintBatch(TimestampMixin, Base):
    __tablename__ = "print_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_name: Mapped[str] = mapped_column(String(120), nullable=False)
    planned_date: Mapped[date | None] = mapped_column(Date)
    material: Mapped[str | None] = mapped_column(String(80))
    color: Mapped[str | None] = mapped_column(String(80))
    estimated_total_print_time_minutes: Mapped[int | None] = mapped_column(Integer)
    estimated_total_filament_grams: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(80), default="nieuw", nullable=False)


class PrintBatchItem(Base):
    __tablename__ = "print_batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    print_batch_id: Mapped[int] = mapped_column(ForeignKey("print_batches.id"), nullable=False)
    print_job_id: Mapped[int] = mapped_column(ForeignKey("print_jobs.id"), nullable=False)
    quantity_in_batch: Mapped[int] = mapped_column(Integer, nullable=False)
