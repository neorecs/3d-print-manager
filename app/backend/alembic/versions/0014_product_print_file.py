"""product print file

Revision ID: 0014_product_print_file
Revises: 0013_user_must_change_password
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_product_print_file"
down_revision = "0013_user_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("products")}
    if "print_file_path" not in columns:
        op.add_column("products", sa.Column("print_file_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("products")}
    if "print_file_path" in columns:
        op.drop_column("products", "print_file_path")
