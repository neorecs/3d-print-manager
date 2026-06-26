from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
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
