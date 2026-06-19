"""Optional relational persistence (PostgreSQL via SQLAlchemy + Alembic).

The API runs in artifact/demo mode without a database; this package is the
production persistence path. Schema is created by Alembic migrations
(`alembic upgrade head`) and populated by `scripts/seed_db.py`.
"""
from wc2026.db.models import Base

__all__ = ["Base"]
