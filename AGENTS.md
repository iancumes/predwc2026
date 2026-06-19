# AGENTS.md

Guidance for coding agents (Codex-compatible). Keep changes minimal, tested, reproducible.

## Architecture
- Monorepo: `packages/wc2026` (engine: data, features, models, evaluation, simulation, db),
  `services/api` (FastAPI, reads artifacts), `apps/web` (Next.js), `migrations` (Alembic).
- The engine is the source of truth; API and web are thin layers over its artifacts.

## Commands
- `make setup` · `make ingest` · `make train` · `make backtest` · `make simulate` · `make freeze`
- `make test` · `make lint` · `make typecheck` · `make build-web`
- CLI: `wc2026 <ingest|train|backtest|simulate|freeze|report|info>`

## Code standards
- Python 3.11+, ruff + mypy must pass (`make lint typecheck`). Line length 100.
- Models implement the `MatchModel` interface (`fit`, `predict_proba`,
  `predict_score_matrix`, `metadata`). Keep 1X2 and score-matrix outputs consistent.
- TypeScript strict on the frontend; client components fetch from the API.

## Mandatory tests
- `make test` must pass. Property tests are non-negotiable: probabilities sum to 1,
  no negative probabilities, exactly one champion per simulation, round-reach is
  monotonic, frozen predictions are pre-kickoff.

## Temporal-leakage rules (critical)
- Every feature must use only data available **before** kickoff (`as_of`).
- Never train on the match being predicted; never recompute a frozen prediction.
- `tests/test_leakage.py` must keep passing.

## Security
- No secrets in git. Use `.env` (gitignored) and `.env.example`. Admin endpoints
  require `WC2026_ADMIN_TOKEN`. Pin dependencies.

## Definition of done
- Clean clone runs `make setup ingest train simulate`; `docker compose up --build` works;
  tests + lint + types pass; web builds; docs updated (`docs/PROGRESS.md`, `docs/DECISIONS.md`).
