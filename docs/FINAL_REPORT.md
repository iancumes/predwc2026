# Final Report — FIFA World Cup 2026 Predictor

Date: 2026-06-18 · Seed: `20260611`

## 1. Status
A complete, reproducible, end-to-end platform is implemented and verified:
real-data ingestion → leakage-free features → five model families → strict
walk-forward backtesting → calibration → vectorised Monte Carlo of the official
48-team bracket → frozen versioned predictions → FastAPI backend → Next.js
frontend → relational schema with Alembic migrations → Docker Compose → tests,
lint, types, CI. All quality gates pass.

## 2. Architecture created
Monorepo: `packages/wc2026` (engine), `services/api` (FastAPI), `apps/web`
(Next.js), `migrations` (Alembic), `scripts`, `docs`. The engine produces
artifacts; the API serves them (artifact-first, Postgres optional); the web app
consumes the API. See `docs/ARCHITECTURE.md`.

## 3. Models compared
Elo (MoV, tournament-weighted), independent Poisson GLM, **Dixon–Coles**
(bivariate Poisson, low-score correction, time decay, analytic gradient),
histogram gradient boosting, and a **calibrated convex ensemble**. Common
`MatchModel` interface; consistent 1X2 and score-matrix outputs.

## 4. Model selected
**Calibrated ensemble** = Dixon–Coles (0.66) + gradient boosting (0.34), 1X2
calibrated (isotonic, chosen on validation). Selection by out-of-sample log loss
then calibration (priority order in `docs/MODELING.md`). Dixon–Coles is the
simpler near-equal fallback (the dominant ensemble component).

## 5. Metrics (walk-forward test, 6,018 matches, 2020–2026)
| Model | Log loss | Brier | RPS | ECE | Acc |
|---|---|---|---|---|---|
| ensemble | **0.8555** | 0.5024 | 0.1659 | 0.0145 | 0.605 |
| ensemble (calibrated) | 0.8583 | 0.5035 | 0.1662 | **0.0127** | 0.605 |
| dixon_coles | 0.8644 | 0.5044 | 0.1668 | 0.0130 | 0.604 |
| boosting | 0.8769 | 0.5152 | 0.1712 | 0.0170 | 0.603 |
| elo | 0.8787 | 0.5165 | 0.1711 | 0.0329 | 0.603 |
| poisson | 0.8829 | 0.5182 | 0.1731 | 0.0400 | 0.595 |
| uniform baseline | 1.0986 | 0.6667 | 0.2392 | 0.1437 | 0.477 |

DC analytic gradient verified (`scipy.check_grad` ≈ 7e-4).

## 6. Simulation
**100,000** Monte Carlo runs from the real post-matchday-1 standings (~18k
sims/s). Champion-probability sum = 1.0; finalists sum = 2; semifinalists sum =
4; round-reach monotonic; R32 = exact qualifiers (all asserted in tests).
Top title chances: Argentina ~30%, Spain ~18%, England ~10%, France ~9%,
Brazil ~7%. Output: `artifacts/simulations/latest.json`.

## 7. Live track record
24 World Cup matches already played were predicted **pre-kickoff** (model refit
per matchday on prior data only): accuracy 0.50, log loss ≈ 1.11 — an honest,
tiny, high-variance sample (matchday 1 had several draws/upsets). The 6,018-match
backtest is the reliable performance indicator.
Output: `artifacts/predictions/track_record.json`.

## 8. Tests
`pytest packages/wc2026/tests tests` → **all pass** (unit, property, integration).
Property tests include: probabilities sum to 1, no negatives, exactly one
champion per simulation, round-reach monotonic, frozen predictions strictly
pre-kickoff, third-place assignment feasibility, seed reproducibility, and the
**anti-leakage** test (features unchanged when future matches are removed).
Lint (ruff) and types (mypy) clean; `next build` succeeds.

## 9. Commands executed (this validation)
```
wc2026 ingest        # 49,475 matches, 1872→2026, 24 played / 48 pending WC
wc2026 train         # calibrated ensemble saved
python scripts/run_backtest.py   # 6,018-match comparison + figures + report
wc2026 simulate --n-sims 100000
wc2026 freeze        # 72 frozen predictions + track record
make test / lint / typecheck     # all green
alembic upgrade head + scripts/seed_db.py   # schema + seed (sqlite verified)
```
API smoke (live): `/health`, `/api/matches`, `/api/tournament/probabilities`,
`/api/model/metrics`, and a frozen match prediction all 200 — captured in
`artifacts/final-validation/`.

**Honesty note on Docker:** the Docker daemon was **not running** in this build
environment, so `docker compose build/up` could **not** be executed here. The
Dockerfiles, entrypoint, and `docker-compose.yml` are written and the compose
file passes `docker compose config` (valid syntax); the CI workflow runs
`docker compose build`. This is the one item validated by configuration + CI
rather than executed locally — see `artifacts/final-validation/docker_build.log`.
The **non-Docker** path (engine + API + web + SQLite migrations/seed) was fully
executed and verified locally.

## 10. Problems encountered & fixes
- Network timeout corrupted the venv's pip → restored via `ensurepip`.
- Elo/Poisson score matrices weren't normalised (Poisson tail truncation) → normalised.
- Frozen `data_cutoff` equalled the match date → set to the true last training
  date so the audit invariant is a strict inequality.
- Two Next dev servers contended on `.next` → run one per project.
- numpy/typing strictness in the ensemble accumulation → rewritten cleanly.

## 11. Assumptions
Official 2026 groups/bracket from FIFA/Wikipedia (membership cross-checked vs
live data); knockouts neutral-venue; ET/penalties folded into an advance
probability; best-thirds assigned by constraint-respecting matching; group
tiebreaks points→GD→GF→lots. See `docs/LIMITATIONS.md`.

## 12. Limitations
Probabilities are estimates, not certainties; no squad/injury data; small live
sample; noisy international data. Analytical/informational only — not betting advice.

## 13. How to run (clean clone)
```bash
make setup
make ingest train simulate freeze
make api        # :8000 (/docs)
make web        # :3000
# or full stack:
make ingest && docker compose up --build
```

## 14. Evidence
- `artifacts/evaluations/` — backtest predictions, summary, report.
- `artifacts/figures/` — model comparison + reliability diagram.
- `artifacts/simulations/latest.json` — 100k simulation.
- `artifacts/predictions/` — frozen predictions, current view, track record.
- `artifacts/final-validation/` — captured API responses + logs from this run.
- Frontend verified rendering live data end-to-end (home, groups, bracket).
