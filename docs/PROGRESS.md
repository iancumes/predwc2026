# PROGRESS

Running log. Newest first. Records what was implemented, commands run, results, errors, next step.

## 2026-06-18 — Iteration 2: models → backtest → simulation → API → web → infra → docs

**Implemented**
- Models: Elo, Poisson GLM, Dixon–Coles (analytic gradient, verified), histogram
  boosting, calibrated ensemble (`ProductionModel`). Leakage-free `features.py`.
- Evaluation: metrics + walk-forward `backtest.py`; full run over 6,018 test matches.
- Simulation: vectorised Monte Carlo (`simulator.py`), official bracket + best-thirds.
- Predictions: frozen/versioned/auditable + live track record.
- API: FastAPI (all endpoints, admin guard, on-demand sim). Web: Next.js (7 pages).
- DB: SQLAlchemy models + Alembic migration + seeder. Docker (db+api+web) + Compose.
- Makefile, CI, full docs set, README, AGENTS/CLAUDE.

**Commands & results**
- backtest → ensemble log loss **0.8555** (best), DC 0.8644, all beat uniform 1.0986.
- train → calibrated ensemble (DC 0.66 / boosting 0.34) saved.
- simulate 100k → Argentina 30.3%, Spain 18.4%, England 10.4%; all sim invariants hold.
- freeze → 72 frozen predictions; track record 24 matches (acc 0.50 — honest, noisy).
- `make test` (42 pass), `make lint` (clean), `make typecheck` (clean), `next build` (ok).
- Alembic `upgrade head` + seed → 15 tables, prob-sum CHECK enforced.
- Frontend verified rendering live API data (screenshot).

**Errors hit & fixed**
- Elo/Poisson score matrices un-normalised → normalised. Frozen cutoff = true last
  training date (strict pre-kickoff). numpy/typing in ensemble accumulation → cleaned.

**Next step** — optional: player/injury features, market-comparison panel,
scheduled post-matchday re-simulation. Core is complete and validated.

## 2026-06-18 — Iteration 1: foundation + data + tournament structure

**Implemented**
- Monorepo skeleton (`apps/`, `services/`, `packages/wc2026/`, `data/`, `artifacts/`, `docs/`).
- Python venv (`.venv`, Python 3.12.7) with pinned scientific + API deps.
- `wc2026` package (editable install): `config`, `teams` (alias/normalisation +
  confederations), `data.ingest`, `data.tournament`.
- Real data: downloaded `martj42/international_results` (CC0) — `results.csv`,
  `shootouts.csv`, `goalscorers.csv` into `data/raw/`.
- Official WC2026 structure verified from Wikipedia (final draw + knockout stage)
  and stored in `resources/wc2026.json` (12 groups A–L, full bracket 73–104,
  third-place slot constraints).

**Commands & results**
- `ingest()` → 49,475 matches, 336 teams, 1872-11-30 .. 2026-06-27; 49,427 played,
  48 scheduled (pending WC fixtures); 2 rows dropped (validation).
- `load_tournament().validate()` → **no warnings**: official group membership
  matches the live fixtures exactly. 72 group fixtures, 24 played (MD1), 48 pending.

**Errors hit & fixed**
- Network timeout corrupted the venv's `pip` (missing `pip._internal.utils`);
  fixed by removing the broken pip dir and restoring via `python -m ensurepip`.

**Next step**
- Model layer: base interface, Elo (online pre-match ratings), features (as_of),
  Poisson, Dixon–Coles (MLE + analytic gradient + time decay), boosting, ensemble,
  calibration.
