# Local Development

## Prerequisites
Python 3.11+ (3.12 recommended), Node 20+ (22 recommended), GNU Make. Docker optional.

## First run
```bash
make setup                 # venv (.venv) + editable engine + web deps
. .venv/bin/activate       # so `wc2026` is on PATH
make ingest                # real data (offline synthetic fallback if no network)
make train                 # fit + save production model
make simulate              # Monte Carlo (WC2026_N_SIMS to scale)
make freeze                # frozen predictions + track record
```
Then, in two terminals:
```bash
make api     # http://localhost:8000  (/docs)
make web     # http://localhost:3000
```
The frontend reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Everyday commands
```bash
make test         # pytest (unit + property + API integration)
make lint         # ruff
make typecheck    # mypy
make build-web    # next build
make backtest     # walk-forward model comparison (slow; writes artifacts/figures)
make report       # consolidated status JSON
wc2026 info       # data + tournament status
```

## Layout
- Engine: `packages/wc2026/src/wc2026/…`; tests in `packages/wc2026/tests`.
- API: `services/api/app` (run with `app-dir` = `services/api`).
- Web: `apps/web/app` (App Router).
- Artifacts (git-tracked outputs): `artifacts/`, `data/processed/`.

## Relational mode (optional)
```bash
export DATABASE_URL="sqlite:////tmp/wc2026.db"   # or a Postgres URL
alembic upgrade head
python scripts/seed_db.py
```

## Tips
- Reproducibility: everything is seeded via `WC2026_SEED`.
- Re-running the pipeline auto-invalidates API caches (mtime-based) — no restart needed.
- If `wc2026` isn't found, activate the venv or re-run `make setup`.
