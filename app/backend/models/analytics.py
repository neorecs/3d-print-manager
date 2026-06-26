from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_weekly_sales: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    estimated_profit: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StockRecommendation(TimestampMixin, Base):
    __tablename__ = "stock_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    current_free_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_sales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommended_stock_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommended_print_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="nieuw", nullable=False)
