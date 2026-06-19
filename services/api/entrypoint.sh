#!/usr/bin/env bash
set -e
cd /app

# Wait for Postgres if a DATABASE_URL points at it.
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "[entrypoint] waiting for database…"
  for i in $(seq 1 30); do
    python - <<'PY' && break || sleep 2
import os, sys
from sqlalchemy import create_engine, text
try:
    create_engine(os.environ["DATABASE_URL"]).connect().execute(text("SELECT 1"))
except Exception as e:
    sys.exit(1)
PY
  done
fi

echo "[entrypoint] running migrations…"
alembic upgrade head || echo "[entrypoint] alembic skipped (no DB)"

if [ -f data/processed/matches.parquet ]; then
  echo "[entrypoint] seeding database from artifacts…"
  python scripts/seed_db.py || echo "[entrypoint] seed skipped"
fi

echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir services/api
