from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class AccountingSale(TimestampMixin, Base):
    __tablename__ = "accounting_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    platform_id: Mapped[int | None] = mapped_column(ForeignKey("platforms.id"), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    invoice_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=21, nullable=False)
    vat_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="concept", nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="manual", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccountingPurchase(TimestampMixin, Base):
    __tablename__ = "accounting_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invoice_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="overig", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=21, nullable=False)
    vat_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), default="onbekend", nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="manual", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccountingDocument(TimestampMixin, Base):
    __tablename__ = "accounting_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_sales.id"), nullable=True)
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_purchases.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="bewaard", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class VatPeriod(TimestampMixin, Base):
    __tablename__ = "vat_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    start_date: Mapped[object] = mapped_column(Date, nullable=False)
    end_date: Mapped[object] = mapped_column(Date, nullable=False)
    sales_vat: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    purchase_vat: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_due: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="concept", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
