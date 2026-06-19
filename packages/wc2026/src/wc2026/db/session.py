"""Database engine/session helpers (PostgreSQL or SQLite for local/dev)."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    # Defaults to a local SQLite file so the schema/seed works with zero setup;
    # docker-compose sets DATABASE_URL to the Postgres service.
    return os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://wc2026:wc2026@localhost:5432/wc2026"
    )


def make_engine(url: str | None = None):
    url = url or database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(url), expire_on_commit=False, future=True)
