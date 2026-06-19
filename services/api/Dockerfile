# FastAPI backend + wc2026 engine. Bundles the generated artifacts so the API
# serves predictions immediately (demo mode), then loads them into Postgres via
# Alembic migrations on startup.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Install the engine + API deps first (better layer caching)
COPY packages/wc2026/pyproject.toml packages/wc2026/README.md ./packages/wc2026/
COPY packages/wc2026/src ./packages/wc2026/src
COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install -e "./packages/wc2026[db]" && pip install -r services/api/requirements.txt

# App code, migrations, and pre-generated data/artifacts (demo mode)
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY scripts ./scripts
COPY services/api ./services/api
COPY data ./data
COPY artifacts ./artifacts

ENV WC2026_ROOT=/app PYTHONPATH=/app/services/api
EXPOSE 8000
ENTRYPOINT ["bash", "services/api/entrypoint.sh"]
