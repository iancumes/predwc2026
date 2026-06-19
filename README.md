# FIFA World Cup 2026 Predictor

An end-to-end, reproducible platform that predicts every FIFA World Cup 2026
match and simulates the whole tournament by Monte Carlo. It ingests **real**
international results, fits and compares several statistical/ML models with
strict walk-forward backtesting, calibrates probabilities, simulates the
official 48-team bracket, and serves everything through a FastAPI backend and a
Next.js frontend.

> **This platform is analytical and informational only.** Probabilities are
> model estimates with uncertainty — not guarantees, betting advice, or a
> promise of any outcome.

---

## 1. What it does

- Per-match probabilities: **1X2**, exact scorelines, expected goals, the full
  **total-goals distribution**, over/under **0.5–3.5**, both-teams-to-score,
  clean-sheet / win-to-nil, and **anytime-goalscorer** probabilities per player.
- Tournament probabilities per team: win group, runner-up, qualify as a best
  third, reach R32 / R16 / QF / SF / Final, and **win the Cup** — with Monte
  Carlo standard errors.
- Live-aware: finished group matches are **locked**; only pending matches are
  forecast and the tournament is re-simulated from the real standings.
- **Auditable, frozen, versioned** predictions: every prediction records the
  model version and data cutoff and is never recomputed retroactively.

## 2. Headline results (reproducible)

**Model comparison** — strict walk-forward backtest, **6,018 test matches
(2020–2026)**, lower log loss is better:

| Model | Log loss | Brier | RPS | ECE | Accuracy |
|---|---|---|---|---|---|
| **ensemble** (DC 0.62 + boosting 0.38) | **0.8542** | 0.5018 | 0.1657 | 0.0112 | 0.608 |
| ensemble (calibrated) | 0.8585 | 0.5036 | 0.1664 | **0.0095** | 0.606 |
| Dixon–Coles | 0.8644 | 0.5044 | 0.1668 | 0.0130 | 0.604 |
| Gradient boosting | 0.8703 | 0.5115 | 0.1699 | 0.0101 | 0.602 |
| Elo | 0.8787 | 0.5165 | 0.1711 | 0.0329 | 0.603 |
| Poisson | 0.8829 | 0.5182 | 0.1731 | 0.0398 | 0.596 |
| baseline: uniform | 1.0986 | 0.6667 | 0.2392 | 0.1437 | 0.477 |

The gradient-boosting learner uses ~29 leakage-free features (Elo and Elo
momentum, weighted form and win rate, goals-for/against and goal-difference
form, rest days, caps/experience, recent head-to-head, confederation,
tournament weight), which lifts it from 0.8769 → **0.8703** log loss and the
ensemble from 0.8555 → **0.8542** (accuracy 0.605 → 0.608, ECE 0.0145 → 0.0112).

**Simulation** — 100,000 Monte Carlo runs from the real standings after
matchday 1 (top title chances): Argentina ~30%, Spain ~18%, England ~10%,
France ~9%, Brazil ~7%. (Numbers move as results come in.)

> Exact figures regenerate from a clean clone; see `artifacts/` and
> `docs/FINAL_REPORT.md`.

## 3. Architecture

Monorepo:

```
apps/web            Next.js + TypeScript + Tailwind frontend
services/api        FastAPI backend (reads artifacts; optional Postgres)
packages/wc2026     Core engine: data, features, models, evaluation, simulation, db
migrations          Alembic migrations (relational schema)
scripts             Backtest runner, DB seeder
data/ artifacts/    Inputs and reproducible outputs
docs/               Architecture, modeling, validation, model/data cards, …
```

The engine is a pure-Python library with a CLI (`wc2026`). The API is a thin
read layer over the artifacts it produces; the frontend is a thin client over
the API. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 4. Requirements

- Python 3.11+ (developed on 3.12), Node 20+ (developed on 22), GNU Make.
- Optional: Docker + Docker Compose (full stack), PostgreSQL (relational mode).

## 5. Quick start (local, no secrets)

```bash
make setup           # venv + Python deps + web deps
make ingest          # download & validate real data (offline fallback included)
make train           # fit + save the production model
make simulate        # Monte Carlo tournament simulation
make freeze          # freeze versioned match predictions
# two terminals:
make api             # FastAPI on http://localhost:8000  (/docs for OpenAPI)
make web             # Next.js on http://localhost:3000
```

`make seed-demo` runs a minimal ingest→train→simulate→freeze→report end-to-end.

## 6. Docker (full stack + Postgres)

```bash
cp .env.example .env          # optional; defaults work
make ingest                   # generate data/ + artifacts/ baked into the API image
docker compose up --build     # db + api (:8000) + web (:3000)
```

The API container runs Alembic migrations and seeds Postgres on startup.

## 6b. Deploy free (static, no backend)

The API is a thin read layer over artifacts, so the whole site ships as a
**static export** — no server, no database, free to host:

```bash
make refresh        # download -> ingest -> train -> simulate -> freeze -> export
make build-web      # static export to apps/web/out (output: "export")
```

`scripts/export_static.py` writes every API response to `apps/web/public/data/**`
and the Next.js app reads those JSON files directly. Deploy `apps/web/out` to any
static host (the repo includes a root `vercel.json` so Vercel builds it
automatically).

**Auto-update (free):** `.github/workflows/update.yml` runs on a daily cron,
pulls the latest results from the CC0 feed (`scripts/download_data.py`, which
*merges* so the fixture schedule is preserved), regenerates everything and
commits the refreshed JSON — Vercel redeploys on the push. Trigger it manually
from the Actions tab any time.

## 7. Environment variables

All optional with safe defaults — see [.env.example](.env.example). Highlights:
`WC2026_SEED`, `WC2026_N_SIMS`, `WC2026_ADMIN_TOKEN` (guards admin endpoints),
`DATABASE_URL`, `NEXT_PUBLIC_API_URL`. **Never commit secrets.**

## 8. CLI

```bash
wc2026 ingest      # download/normalise/validate matches
wc2026 train       # fit + save production model
wc2026 backtest    # walk-forward model comparison (also: python scripts/run_backtest.py)
wc2026 simulate    # Monte Carlo simulation (--n-sims N)
wc2026 freeze      # freeze versioned predictions
wc2026 report      # consolidated status report
wc2026 info        # data + tournament status
```

## 9. API

`GET /health`, `/api/teams`, `/api/teams/{code}`, `/api/matches`,
`/api/matches/{id}`, `/api/matches/{id}/prediction`, `/api/groups`,
`/api/groups/{id}`, `/api/tournament/probabilities`, `/api/tournament/bracket`,
`/api/model/metrics`, `/api/model/calibration`, `POST /api/simulations`,
`POST /api/admin/ingest`, `POST /api/admin/train`. Full reference:
[docs/API.md](docs/API.md). Interactive docs at `/docs`.

## 10. Frontend pages

Home, Matches + match detail (1X2, xG, scorelines, factors), Groups (live
tables + qualification %), Bracket (road-to-final probabilities), Teams + team
detail, Track record, Methodology. Handles loading / error / empty / demo
states.

## 11. Testing, lint, types

```bash
make test        # pytest: unit, property (probabilities sum to 1, one champion, …), integration (API)
make lint        # ruff
make typecheck   # mypy
make build-web   # next build
```

## 12. Models

Elo (margin-of-victory, tournament-weighted), independent Poisson GLM,
**Dixon–Coles** (bivariate Poisson, low-score correction, time decay, analytic
gradient), gradient boosting (histogram GBM), and a **calibrated convex
ensemble**. Details and the selection rationale:
[docs/MODELING.md](docs/MODELING.md), [docs/MODEL_CARD.md](docs/MODEL_CARD.md).

## 13. Data sources & licenses

Primary: [`martj42/international_results`](https://github.com/martj42/international_results)
(**CC0**) — all international men’s matches since 1872, including live 2026
fixtures. Official 2026 groups/bracket verified from FIFA / Wikipedia. Engine
code: MIT. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) and
[docs/DATA_CARD.md](docs/DATA_CARD.md).

## 14. Limitations

A probability is not a certainty; international data is noisy; squad/injury
information is not yet modelled; the early-tournament track record is a tiny
sample. **Corners and cards are not modelled** — the free CC0 results feed has
no match-event data; they would need a (paid) events provider. Anytime-scorer
numbers assume recent scorers are in the squad and cannot see call-ups/injuries.
See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## 15. Troubleshooting

- *API shows demo/empty state* → run `make ingest train simulate freeze`.
- *Frontend can’t reach API* → set `NEXT_PUBLIC_API_URL` (build-time) to the API URL.
- *`wc2026: command not found`* → activate the venv (`. .venv/bin/activate`) or run `make setup`.
- *Admin endpoint 503/401* → set `WC2026_ADMIN_TOKEN` and send `Authorization: Bearer <token>`.

## 16. Next steps

Player/injury features, market-consensus comparison, automated post-matchday
re-simulation, more external data adapters. See
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
