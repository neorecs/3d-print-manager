from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class CostSetting(TimestampMixin, Base):
    __tablename__ = "cost_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(10, 4), default=0, nullable=False)


class OrderProfitCalculation(TimestampMixin, Base):
    __tablename__ = "order_profit_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    sale_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    filament_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    packaging_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    electricity_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    estimated_profit: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
