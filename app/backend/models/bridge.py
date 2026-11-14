from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PrinterBridge(Base):
    """A small agent in another network that talks to Bambu printers there over LAN.

    Only the agent connects out (HTTPS) to this app; nothing has to be opened in the
    remote network. The token is stored as a SHA-256 hash and shown once.
    """

    __tablename__ = "printer_bridges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_hint: Mapped[str] = mapped_column(String(12), nullable=False)
    agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BridgeCommand(Base):
    """A command for a bridge printer; the agent picks it up on its next sync."""

    __tablename__ = "bridge_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bridge_id: Mapped[int] = mapped_column(ForeignKey("printer_bridges.id", ondelete="CASCADE"), nullable=False, index=True)
    printer_id: Mapped[int] = mapped_column(ForeignKey("bambu_printers.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="wachtrij", nullable=False)
    result_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
