# Limitations & Assumptions

## Interpretation
- **A probability is not a certainty.** A 70% favourite still loses ~3 times in
  10. Outputs are estimates with uncertainty, for analysis only — not betting
  advice or any guarantee.
- The live World Cup track record is a **tiny, high-variance sample** (matchday 1
  featured several draws/upsets). Judge model quality by the 6,018-match
  backtest, not a handful of matches.

## Data
- No squad, injury, lineup, suspension, weather, altitude, or travel data — only
  team-level match facts. Form/strength implicitly absorb some of this.
- International data is noisy (friendlies, experimental lineups); older eras and
  minor nations have thinner/less reliable coverage. Mitigated by time decay,
  importance weighting, and recent training windows.
- Community data may lag or contain occasional errors; on conflict the official
  feed wins.

## Modeling
- Goal models assume (near-)independent team scoring rates with the Dixon–Coles
  low-score correction; true within-match dynamics are richer.
- Knockout extra-time/penalties are approximated by a single advance probability
  `P(win) + P(draw)·share` with `share = P_win/(P_win+P_loss)` — reasonable but
  not a literal ET/shootout model.
- Knockout matches are treated as neutral venue (host home advantage in KO rounds
  is not modelled).
- The best-thirds → bracket assignment respects FIFA's per-slot group constraints
  via a constraint-solving matching; for a specific combination it may differ from
  FIFA's exact canonical row, with negligible effect on aggregate probabilities.

## Scope
- Group tiebreakers implement the official order (points, GD, GF); deep head-to-head
  among 3-way ties falls back to drawing-of-lots (the official final criterion),
  a negligible-impact approximation.
- Market odds are not used as a feature (kept clean; documented as future
  comparison-only reference).

## Operational
- The full backtest is compute-heavy (refits every model each fold). Use the
  provided window/steps or shrink them for quick iterations.
