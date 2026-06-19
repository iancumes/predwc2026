"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18

Creates the full schema from the ORM metadata. Using create_all here keeps the
single source of truth in wc2026.db.models while still being driven by
`alembic upgrade head`.
"""
from alembic import op

from wc2026.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
