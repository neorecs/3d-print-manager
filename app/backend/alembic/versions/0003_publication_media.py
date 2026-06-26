"""platform-specific publication media selection

Revision ID: 0003_publication_media
Revises: 0002_costs
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_publication_media"
down_revision = "0002_costs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "product_publication_media" in set(inspector.get_table_names()):
        return

    op.create_table(
        "product_publication_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_publication_id", sa.Integer(), sa.ForeignKey("product_platform_publications.id"), nullable=False),
        sa.Column("product_media_id", sa.Integer(), sa.ForeignKey("product_media.id"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("product_publication_media")
