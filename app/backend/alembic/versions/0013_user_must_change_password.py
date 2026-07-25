"""add required password change flag

Revision ID: 0013_user_must_change_password
Revises: 0012_auth_users_audit
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0013_user_must_change_password"
down_revision = "0012_auth_users_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")} if "users" in inspector.get_table_names() else set()
    if "must_change_password" not in columns:
        op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")} if "users" in inspector.get_table_names() else set()
    if "must_change_password" in columns:
        op.drop_column("users", "must_change_password")
