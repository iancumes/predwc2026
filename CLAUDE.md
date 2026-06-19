# CLAUDE.md

Instructions for Claude Code in this repo. (Mirror of AGENTS.md — keep both in sync.)

## Architecture
- Monorepo: `packages/wc2026` (engine), `services/api` (FastAPI), `apps/web` (Next.js),
  `migrations` (Alembic). The engine produces artifacts under `artifacts/`; the API
  serves them; the web app consumes the API.

## Commands
- Setup/run: `make setup ingest train backtest simulate freeze`, `make api`, `make web`.
- Quality: `make test`, `make lint`, `make typecheck`, `make build-web`.
- CLI entrypoint: `wc2026` (see `packages/wc2026/src/wc2026/cli.py`).

## Conventions
- Outcome order is always `[home, draw, away]`. Score matrix `M[i,j] = P(home i, away j)`.
- New models subclass `MatchModel`; keep `predict_proba` and `predict_score_matrix` consistent.
- Config/seeds live in `wc2026/config.py`. Use the seed; runs must be reproducible.

## Mandatory tests & leakage
- `make test` must stay green, including property tests and `tests/test_leakage.py`.
- No temporal leakage: features are `as_of` (pre-kickoff) only; frozen predictions are immutable.

## Security
- Never commit secrets. `.env` is gitignored; document new vars in `.env.example`.

## Definition of done
- Clean clone → `make setup ingest train simulate` works; `docker compose up --build` works;
  tests/lint/types pass; web builds; `docs/PROGRESS.md` + `docs/DECISIONS.md` updated.
