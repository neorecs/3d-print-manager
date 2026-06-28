from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import TimestampMixin


class Platform(TimestampMixin, Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    credentials: Mapped[list["PlatformCredential"]] = relationship(back_populates="platform")


class PlatformCredential(TimestampMixin, Base):
    __tablename__ = "platform_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    key_name: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    platform: Mapped[Platform] = relationship(back_populates="credentials")


class PlatformProductLink(TimestampMixin, Base):
    __tablename__ = "platform_product_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    internal_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(255))
    external_variant_id: Mapped[str | None] = mapped_column(String(255))
    sku: Mapped[str | None] = mapped_column(String(120))


class PlatformImportLog(TimestampMixin, Base):
    __tablename__ = "platform_import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    import_type: Mapped[str] = mapped_column(String(60), default="orders", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="nieuw", nullable=False)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    since: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesMarket(TimestampMixin, Base):
    __tablename__ = "sales_markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    primary_language: Mapped[str] = mapped_column(String(10), default="nl", nullable=False)
    additional_languages: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
