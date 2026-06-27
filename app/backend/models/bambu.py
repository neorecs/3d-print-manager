from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import TimestampMixin


class BambuPrinter(TimestampMixin, Base):
    __tablename__ = "bambu_printers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host: Mapped[str] = mapped_column(String(255))
    mqtt_port: Mapped[int] = mapped_column(Integer, default=8883)
    access_code_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    connection_mode: Mapped[str] = mapped_column(String(50), default="lan")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    last_status: Mapped[str] = mapped_column(String(50), default="onbekend")
    status_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    printer_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    print_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nozzle_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    bed_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    chamber_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_task: Mapped[str | None] = mapped_column(String(255), nullable=True)
