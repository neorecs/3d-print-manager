from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    internal_title: Mapped[str | None] = mapped_column(String(255))
    short_description: Mapped[str | None] = mapped_column(Text)
    long_description: Mapped[str | None] = mapped_column(Text)
    sales_description: Mapped[str | None] = mapped_column(Text)
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str | None] = mapped_column(String(120))
    internal_category: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(60), default="concept", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    media: Mapped[list["ProductMedia"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    tags: Mapped[list["ProductTag"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductMedia(TimestampMixin, Base):
    __tablename__ = "product_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), default="image", nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped[Product] = relationship(back_populates="media")


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(180), nullable=False)
    sku: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(80))
    material: Mapped[str | None] = mapped_column(String(80))
    size: Mapped[str | None] = mapped_column(String(80))
    finish: Mapped[str | None] = mapped_column(String(80))
    print_file_path: Mapped[str | None] = mapped_column(String(500))
    estimated_print_time_minutes: Mapped[int | None] = mapped_column(Integer)
    estimated_filament_grams: Mapped[float | None] = mapped_column(Float)
    weight_grams: Mapped[float | None] = mapped_column(Float)
    length_mm: Mapped[float | None] = mapped_column(Float)
    width_mm: Mapped[float | None] = mapped_column(Float)
    height_mm: Mapped[float | None] = mapped_column(Float)
    default_sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    action_sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cost_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(back_populates="variants")


class ProductTag(Base):
    __tablename__ = "product_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String(80), nullable=False)

    product: Mapped[Product] = relationship(back_populates="tags")


class ProductPlatformPublication(TimestampMixin, Base):
    __tablename__ = "product_platform_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(255))
    external_listing_id: Mapped[str | None] = mapped_column(String(255))
    publication_status: Mapped[str] = mapped_column(String(80), default="niet_gepubliceerd", nullable=False)
    platform_title: Mapped[str | None] = mapped_column(String(255))
    platform_description: Mapped[str | None] = mapped_column(Text)
    platform_category: Mapped[str | None] = mapped_column(String(120))
    platform_tags: Mapped[str | None] = mapped_column(Text)
    platform_price_override: Mapped[float | None] = mapped_column(Numeric(10, 2))
    platform_shipping_profile_id: Mapped[str | None] = mapped_column(String(120))
    last_synced_at: Mapped[str | None] = mapped_column(String(80))
    last_error: Mapped[str | None] = mapped_column(Text)


class ProductPublicationMedia(TimestampMixin, Base):
    __tablename__ = "product_publication_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_publication_id: Mapped[int] = mapped_column(ForeignKey("product_platform_publications.id"), nullable=False)
    product_media_id: Mapped[int] = mapped_column(ForeignKey("product_media.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductVariantPlatformLink(TimestampMixin, Base):
    __tablename__ = "product_variant_platform_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    external_variant_id: Mapped[str | None] = mapped_column(String(255))
    external_sku: Mapped[str | None] = mapped_column(String(120))
    external_inventory_id: Mapped[str | None] = mapped_column(String(255))
