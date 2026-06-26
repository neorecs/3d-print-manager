"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-25
"""

from alembic import op

from database import Base
from models import *  # noqa: F401,F403

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
