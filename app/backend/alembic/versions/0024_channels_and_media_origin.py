"""channel profiles: manual placement, EAN per variant, photo origin

Revision ID: 0024_channels_media
Revises: 0023_notifications
"""

from alembic import op
import sqlalchemy as sa


revision = "0024_channels_media"
down_revision = "0023_notifications"
branch_labels = None
depends_on = None

COLUMNS = (
    ("product_media", sa.Column("ai_edited", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("product_media", sa.Column("source_media_id", sa.Integer(), nullable=True)),
    ("product_variants", sa.Column("ean", sa.String(length=14), nullable=True)),
    ("product_platform_publications", sa.Column("external_url", sa.String(length=500), nullable=True)),
    ("product_platform_publications", sa.Column("placed_manually", sa.Boolean(), nullable=False, server_default=sa.false())),
)


def upgrade() -> None:
    # A fresh database already has these columns from the initial create_all.
    inspector = sa.inspect(op.get_bind())
    for table, column in COLUMNS:
        existing = {item["name"] for item in inspector.get_columns(table)}
        if column.name not in existing:
            op.add_column(table, column)


def downgrade() -> None:
    for table, column in reversed(COLUMNS):
        op.drop_column(table, column.name)
