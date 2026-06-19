# Deployment

## Docker Compose (recommended)
```bash
cp .env.example .env                 # set WC2026_ADMIN_TOKEN at minimum for admin
make ingest                          # generate data/ + artifacts/ baked into the API image
docker compose up --build            # db (5432) + api (8000) + web (3000)
```
- `db`: Postgres 16 with a healthcheck.
- `api`: builds the engine + API, **bundles the generated artifacts**, and on
  startup runs `alembic upgrade head` then `scripts/seed_db.py` before serving.
- `web`: Next.js standalone build; `NEXT_PUBLIC_API_URL` is baked at build time
  (default `http://localhost:8000`).

Tear down: `docker compose down -v`.

## Configuration
See `.env.example`. Important for production:
- `WC2026_ADMIN_TOKEN` — required to enable `POST /api/admin/*` (else 503).
- `DATABASE_URL` — Compose sets the Postgres URL automatically.
- `WC2026_CORS_ORIGINS` — restrict to your web origin(s) in production.
- `NEXT_PUBLIC_API_URL` — must be the **browser-reachable** API URL (build arg).

## Production notes
- Put the API behind a reverse proxy (TLS) and rate-limit `POST /api/simulations`
  and admin endpoints. Timeouts/retries are applied to outbound data fetches.
- The frontend is fully static/standalone and can be served by any Node host or CDN+Node.
- Scheduled refresh: run `wc2026 ingest && wc2026 simulate && wc2026 freeze` on a
  cron after each matchday (a GitHub Actions schedule is a good fit). Do **not**
  auto-retrain destructively; keep prior frozen predictions (the store is append-only).

## CI
`.github/workflows/ci.yml` runs lint, types, ingest, tests, a SQLite migration
smoke test, the web build, and a `docker compose build` smoke test.
