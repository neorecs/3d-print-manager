"""printer bridges for Bambu printers outside the local network

Revision ID: 0025_printer_bridges
Revises: 0024_channels_media
"""

from alembic import op
import sqlalchemy as sa


revision = "0025_printer_bridges"
down_revision = "0024_channels_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A fresh database already has these from the initial create_all.
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "printer_bridges" not in tables:
        op.create_table(
            "printer_bridges",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("token_hint", sa.String(length=12), nullable=False),
            sa.Column("agent_version", sa.String(length=50), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_ip", sa.String(length=64), nullable=True),
            sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "bridge_commands" not in tables:
        op.create_table(
            "bridge_commands",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bridge_id", sa.Integer(), sa.ForeignKey("printer_bridges.id", ondelete="CASCADE"), nullable=False),
            sa.Column("printer_id", sa.Integer(), sa.ForeignKey("bambu_printers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(length=40), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="wachtrij"),
            sa.Column("result_message", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("picked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_bridge_commands_bridge_id", "bridge_commands", ["bridge_id"])
    columns = {item["name"] for item in inspector.get_columns("bambu_printers")}
    if "bridge_id" not in columns:
        with op.batch_alter_table("bambu_printers") as batch:
            batch.add_column(sa.Column("bridge_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_bambu_printers_bridge", "printer_bridges", ["bridge_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("bambu_printers") as batch:
        batch.drop_constraint("fk_bambu_printers_bridge", type_="foreignkey")
        batch.drop_column("bridge_id")
    op.drop_index("ix_bridge_commands_bridge_id", table_name="bridge_commands")
    op.drop_table("bridge_commands")
    op.drop_table("printer_bridges")
