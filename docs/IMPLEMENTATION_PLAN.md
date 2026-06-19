# Implementation Plan

Status legend: ✅ done · ◻️ future.

## Phases (executed in order)
1. ✅ Inspect repo, set up venv + pinned deps, monorepo skeleton.
2. ✅ Ingestion: real martj42 data (CC0) + validation + normalisation + offline fallback.
3. ✅ Tournament structure: official 2026 groups/bracket resource, cross-checked vs live fixtures.
4. ✅ Models + common interface: Elo, Poisson, Dixon–Coles (analytic gradient), boosting.
5. ✅ Leakage-free feature builder (`as_of`) + property test.
6. ✅ Metrics + strict walk-forward backtest; ensemble weights + calibration on validation.
7. ✅ Model comparison run (6,018 test matches) + figures + report.
8. ✅ Production model (calibrated ensemble) + save/load.
9. ✅ Vectorised Monte Carlo simulator (48 teams, official bracket, best-thirds, ET/pens).
10. ✅ Frozen, versioned, auditable predictions + live track record.
11. ✅ FastAPI backend (all endpoints, admin guard, on-demand sim) over artifacts.
12. ✅ Next.js frontend (home, matches, groups, bracket, teams, track record, methodology).
13. ✅ Relational schema (SQLAlchemy) + Alembic migrations + seeder.
14. ✅ Tests (unit, property, integration), ruff, mypy — all green.
15. ✅ Docker (db + api + web) + Compose; Makefile; CI workflow.
16. ✅ Documentation set (this folder) + README + AGENTS/CLAUDE.
17. ✅ Final validation run + FINAL_REPORT + `artifacts/final-validation/`.

## Future work (◻️)
- Player/injury/lineup features behind a licensed feed.
- Market-consensus comparison panel (reference only).
- Scheduled post-matchday re-ingest + re-simulate (GitHub Actions cron).
- Optional XGBoost/LightGBM/CatBoost components behind the `MatchModel` interface.
- API read-through to Postgres (currently artifact-first; DB is seeded/queried separately).

## Working agreements
- Update `docs/PROGRESS.md` and `docs/DECISIONS.md` each iteration.
- No task marked done unless executed and tested. No secrets in git. Reproducible (seeded).
