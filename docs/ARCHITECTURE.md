# Architecture

## Overview

```
                 ┌─────────────────────────────────────────────┐
   real data ───▶│  packages/wc2026 (engine, pure Python + CLI) │
 (martj42 CC0)   │  data → features → models → eval → simulation│
                 └───────────────┬─────────────────────────────-┘
                                 │ writes
                                 ▼
                         artifacts/ + data/processed
                                 │ reads                 ┌────────────┐
                                 ▼                       │ Postgres   │
                         services/api (FastAPI) ◀────────│ (optional) │
                                 │ HTTP/JSON             └────────────┘
                                 ▼
                          apps/web (Next.js)
```

The **engine** owns all domain logic and is independently testable. The **API**
is a thin read layer over the engine's artifacts (and optionally a relational
DB). The **web** app is a thin client over the API.

## Components

### `packages/wc2026` (engine)
- `config.py` — paths, seeds, model hyperparameters (single source of knobs).
- `teams.py` — name normalisation/aliases, codes, confederations.
- `data/ingest.py` — download → validate → normalise → `data/processed/matches.parquet`.
- `data/tournament.py` — official 2026 structure (`resources/wc2026.json`) joined to live fixtures.
- `features.py` — leakage-free (`as_of`) feature builder (Elo, form, rest, context).
- `models/` — `base` (interface), `elo`, `poisson`, `dixon_coles`, `boosting`,
  `ensemble`, `calibration`, `production` (the deployed calibrated ensemble).
- `evaluation/` — `metrics` (log loss, Brier, RPS, ECE, calibration) and
  `backtest` (walk-forward).
- `simulation/simulator.py` — vectorised Monte Carlo of the full bracket.
- `predictions.py` — frozen, versioned, auditable predictions + track record.
- `standings.py` — live group tables from locked results.
- `db/` — SQLAlchemy models + session (relational persistence).
- `cli.py` — `wc2026` command.

### `services/api`
FastAPI app (`app/main.py`) + an artifact-backed `store.py`. Read endpoints
degrade to `demo_mode` when artifacts are missing. Admin endpoints
(ingest/train) are token-guarded and run in the background with an idempotency lock.

### `apps/web`
Next.js (App Router) + TypeScript + Tailwind. Client components fetch the API;
every page handles loading / error / empty states. Mobile-first.

### Persistence
- **Default (demo):** file artifacts (`artifacts/`, `data/processed/`). Zero setup.
- **Relational:** Alembic migrations create the schema (`migrations/`); `scripts/seed_db.py`
  loads artifacts into Postgres. Used by Docker Compose.

## Data flow (one cycle)
1. `ingest` → validated `matches.parquet` (+ ingestion report).
2. `train` → fit base models, learn ensemble weights + calibrator → `production.pkl`.
3. `backtest` → walk-forward metrics + figures (model selection evidence).
4. `simulate` → per-team tournament probabilities → `simulations/latest.json`.
5. `freeze` → per-match frozen predictions + track record.
6. API serves all of the above; web renders it.

## Reproducibility
Single global seed (`WC2026_SEED`); all randomness flows through seeded
generators. Same code + same data + same seed → identical artifacts.
