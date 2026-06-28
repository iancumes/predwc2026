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

---

## Web UI redesign — interactive broadcast theme (2026-06-28)

Reworked `apps/web` from the generic light-theme scaffold into a distinctive,
animated, broadcast-style product:

- **Design system** (`globals.css`, `tailwind.config.ts`): dark "stadium at
  night" surface palette, signature emerald→cyan→violet brand gradient, glass
  cards, ambient glow backdrop, Sora/Inter type pairing (loaded at runtime via
  Google Fonts `<link>`, no build-time fetch), reusable keyframes (fade-up,
  scale-in, bar-grow, stagger, float) with a `prefers-reduced-motion` guard.
- **Country flags** (`app/lib/flags.ts` + `Flag` component): every team shows
  its national flag (flagcdn.com SVG/PNG, incl. gb-eng/gb-sct) with a robust
  initials fallback on missing mapping *or* image load error.
- **Interactive team peek** (`app/components/TeamModal.tsx`): a global, animated
  modal opened by tapping any team anywhere — title odds, round-by-round
  progression bars, recent W/D/L form strip, and group fixtures, with Escape /
  backdrop close and scroll lock.
- **Knockout bracket** (`app/bracket/page.tsx`): a horizontally-scrollable
  bracket tree from the Round of 32 → Final (+ third-place play-off) with flags;
  group slots resolve to the real qualified nation once a group is mathematically
  locked, the rest show clear placeholders. A toggle flips to the reach-odds
  heatmap.
- Refreshed Home (hero + podium), Matches (scoreboard header), Groups, Teams
  (search + click-to-peek), and the team/match detail pages for the dark theme.
- `make build-web` passes (146 static routes exported).

## Auto-refresh schedule → Guatemala time
`.github/workflows/update.yml` cron pinned to America/Guatemala (UTC-6, no DST):
`0 14 * * *` (08:00 GT) and `59 5 * * *` (23:59 GT).

## Live knockout bracket — real qualifiers + auto-advancing (2026-06-28)

The bracket now resolves to real nations and advances with results, not just
probabilities:

- **`wc2026/bracket.py`** — a deterministic, leakage-free resolver. Uses played
  results only: group winners/runners-up from live standings; the eight best
  third-placed teams allocated to their R32 slots (FIFA allowed-group rule,
  reusing the simulator's constraint assignment) as a *predictor*; and the real
  knockout fixtures from the feed as *ground truth* (teams + score + winner,
  with penalty shootouts read from `shootouts.csv`). Winners propagate up the
  tree round by round.
- **`tournament.py`** — `load_tournament` now splits the live feed into
  `fixtures` (group stage) and `knockout_fixtures` (cross-group R32+ ties). This
  fixes `validate()` (no more cross-group warnings once knockouts appear) and the
  pending-group-match counts.
- **`store.bracket()`** exposes `resolved` → exported in `bracket.json`.
- **UI** — the bracket tree renders real flags, scores, a highlighted winner per
  tie, dates, a "played N/32" counter and a champion banner, all keeping the dark
  theme + animations. The home "Upcoming matches" falls back to upcoming
  knockout ties once the group stage ends.
- Tests: `packages/wc2026/tests/test_bracket.py` (resolver coverage, winner
  propagation, and an explicit no-leakage test). Full suite green.

All of this is regenerated by the twice-daily auto-update action, so the bracket
fills in and advances automatically as the real tournament unfolds.

## Predictions restored for knockout ties (2026-06-28)

Splitting knockout fixtures out of `fixtures` had dropped them from the
predictions pipeline and the match list. Restored end-to-end:
- `predictions.freeze_world_cup` now predicts group **and** knockout fixtures.
- `store.matches` / `match_detail` include knockout ties with a `stage` label
  (and `home_code`/`away_code`); `bracket.resolve_bracket` now carries each
  tie's `match_id`.
- Web: every bracket match links to its full prediction page (1X2, goals,
  scorelines, total-goals, anytime scorers) while team clicks still open the
  peek modal; the Matches page gained a "Knockouts" filter + round badges; the
  home upcoming-knockout cards link straight to the prediction page.
