# Model Card — WC2026 Production Ensemble

**Model:** calibrated convex ensemble of Dixon–Coles (0.66) + histogram gradient
boosting (0.34), with Elo and Poisson as evaluated baselines (≈0 weight).
**Version id:** `production_ensemble-<hash>` (hash of metadata + data cutoff).

## Intended use
Estimate match (1X2, scoreline, goals) and tournament (round-reach, champion)
probabilities for FIFA World Cup 2026. **Analytical/informational only** — not
betting advice or a guarantee.

## Inputs
Pre-kickoff (`as_of`) features only: pre-match Elo & Elo diff, exponentially
weighted recent form (PPG, GF, GA), rest days, neutrality, host flag, match
importance. No squad/injury/lineup data.

## Training data
martj42/international_results (CC0), matches ≥ 1994/2008 depending on component,
with exponential time decay (recent matches weighted more).

## Performance (walk-forward test, 6,018 matches 2020–2026)
Log loss 0.8555 (raw) / 0.8583 (calibrated); Brier 0.502; RPS 0.166;
ECE 0.013; accuracy 0.605. Beats uniform (1.099) and every single model.
See VALIDATION.md.

## Calibration
1X2 probabilities calibrated on validation (none/temperature/isotonic chosen by
log loss with Occam margins + smoothing). ECE ≈ 0.013 on test.

## Limitations & ethical considerations
A probability is not a certainty (a 70% favourite loses ~30% of the time).
International football is high-variance; early-tournament samples are tiny.
No personal data is used. Do not use for wagering or high-stakes decisions.

## Maintenance
Reproducible from a clean clone (`make ingest train backtest simulate`),
seed-controlled. Retrain by re-running `wc2026 train` after new results ingest.
