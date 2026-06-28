# Decisions (ADR-style log)

Newest first. Each entry: decision, rationale, alternatives, status.

## D-012 Richer goal features and markets; anytime-goalscorer layer
Boosting feature set expanded to ~29 leakage-free signals (Elo momentum, win
rate, GD form, caps/experience, recent head-to-head, confederation): boosting
0.8769 → 0.8703, ensemble 0.8555 → 0.8542 log loss. `market_probabilities` now
emits the full total-goals distribution, O/U 0.5–3.5, BTTS, clean-sheet and
win-to-nil. A transparent `GoalscorerModel` (time-decayed scoring share ×
expected goals → anytime-scorer probability) is attached to pending fixtures.
Corners/cards deferred — absent from the free feed. Status: done.

## D-011 Auto-update via GitHub Actions + merge-not-overwrite download
`.github/workflows/update.yml` (daily cron + manual dispatch) refreshes data,
retrains, re-simulates, re-freezes, re-exports and commits the JSON; Vercel
redeploys on push. `scripts/download_data.py` **merges** the CC0 feed on
`(date, home, away)`, preferring rows with a real score, so the committed 2026
fixture schedule is never lost and real results progressively replace
placeholders. Status: done.

## D-010 Free deployment as a static export (no backend)
The FastAPI service is a thin read layer over artifacts, so `scripts/export_static.py`
materialises every endpoint to `apps/web/public/data/**` and the Next.js app reads
those JSON files client-side. `next.config` defaults to `output: "export"`; the
two dynamic routes use `generateStaticParams`. Result: a pure static `out/` that
hosts free on Vercel (root `vercel.json`) with no serverless/DB and no cold starts.
Docker still works via `NEXT_OUTPUT=standalone`. Status: done.

## D-009 Honest data cutoff for frozen predictions
For already-played matches, `data_cutoff` is the **actual last training date**
(strictly before kickoff), not the match date — so the audit invariant
"cutoff < kickoff" holds literally. Status: done.

## D-008 Production model = calibrated ensemble
Deploy the calibrated convex ensemble (DC 0.66 + boosting 0.34). It wins
out-of-sample log loss and has the best calibration. Dixon–Coles alone is a
close, simpler fallback. Status: done.

## D-007 Histogram gradient boosting instead of XGBoost/LightGBM/CatBoost
Chose scikit-learn `HistGradientBoosting` (a LightGBM-style algorithm). It keeps
the project pure-Python and reproducible with **no compiled native deps**, which
matters more here than the marginal accuracy of the alternatives — and the
ensemble already captures most of the boosting signal. Alternatives remain
documented; swap-in is straightforward behind the `MatchModel` interface.
Status: done.

## D-006 Analytic gradient for Dixon–Coles
Implemented the exact gradient (verified vs `scipy.check_grad`, err ≈ 7e-4).
Cuts a fit to <1s, making per-fold refitting in the backtest feasible.
Status: done.

## D-005 Official 2026 structure as a verified resource, membership cross-checked
Group letters (A–L) and the full bracket (incl. the third-place slot
constraints) are stored in `resources/wc2026.json`, verified from FIFA/Wikipedia.
Group **membership** is cross-checked at load time against the live fixtures
(passes with zero warnings). Rationale: the live feed has fixtures but not the
official lettering/bracket; this separation keeps both authoritative.
Status: done.

## D-004 Best-thirds assignment via the 495-combination table
FIFA defines a slot↔group mapping for each of C(12,8)=495 third-place
combinations. We solve a constraint-respecting assignment once per combination
(Hungarian algorithm) and look it up by bitmask per simulation — exact
constraints, fully vectorised. Status: done.

## D-003 Knockouts via a precomputed advance-probability matrix
Extra time + penalties are folded into a single neutral-venue "advance
probability" `P[i,j]`, derived from the model's 1X2 with the draw mass split
toward the stronger side (`P(win)+P(draw)·share`). Enables fully vectorised
knockout simulation at ~18k sims/sec. Assumption documented in LIMITATIONS.
Status: done.

## D-002 Artifact-first persistence; Postgres optional
The engine writes file artifacts; the API reads them (zero-setup demo). A full
SQLAlchemy schema + Alembic migrations + seeder provide the relational path used
by Docker. Rationale: a clean clone must run with no database. Status: done.

## D-001 Primary data source martj42/international_results (CC0)
Comprehensive (1872–present), permissively licensed, and **already includes the
live 2026 fixtures/results**. An offline synthetic fallback keeps the pipeline
runnable with no network. football-data.org is the documented alternative
adapter. Status: done.

## Rejected / deferred
- **Neural net match model** — data volume/cleanliness don't justify it; GBM +
  DC dominate on the priority metrics. Deferred.
- **Random-walk train/test split** — rejected (temporal leakage); walk-forward only.
- **Player/injury features** — deferred until a reliable, licensed feed exists;
  the system runs without them.

## D-010 Dark broadcast UI + client-side flags/animations (no new deps)
The web app moved to a dark, animated "broadcast graphics" theme to shed the
generic look. Animations are pure CSS/Tailwind keyframes and the team-peek modal
is a small React context — deliberately **no animation library** (framer-motion
etc.) to keep the static export light and the build dependency-free. Flags are
served from flagcdn.com (real SVG/PNG, cross-OS consistent) with an initials
fallback, rather than emoji flags (which don't render on Windows). Fonts load via
a runtime Google Fonts `<link>` instead of `next/font` to avoid build-time
network fetches. Status: done.

## D-011 Knockout bracket resolves only locked group slots
The bracket tree renders the official 2026 structure (R32→Final) and fills a slot
with the real nation only when its group is mathematically decided
(`p_win_group`/`p_runner_up` ∈ {0,1}); third-placed and winner/loser slots stay
as labelled placeholders until determined. Rationale: never show a team in a slot
it isn't guaranteed. Status: done.

## D-012 Result-refresh schedule in Guatemala time
Auto-update cron pinned to America/Guatemala: 08:00 and 23:59 local
(`0 14 * * *`, `59 5 * * *` UTC). Status: done.
