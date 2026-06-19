# Validation & Backtesting

## Protocol
Strictly temporal **walk-forward** validation — never a random `train_test_split`.

```
train (< val_start) | validation [val_start, test_start) | test [test_start, end)
```

- Base models are **refit every fold** on data strictly before the fold and
  predict only that fold (no future leakage).
- Ensemble weights and the calibrator are learned **only on the validation
  period**, then applied unchanged to test — so meta-parameters never see test
  outcomes.
- Defaults: `val_start=2016-01-01`, `test_start=2020-01-01`, `test_end=2026-06-10`,
  180-day folds (`scripts/run_backtest.py`).

## Metrics
Log loss (primary), Brier, RPS, Expected Calibration Error, accuracy, confusion
matrix, reliability curve. Implemented and unit-tested in
`wc2026/evaluation/metrics.py`.

## Results (test set, 6,018 matches, 2020–2026)

| Model | Log loss | Brier | RPS | ECE | Accuracy |
|---|---|---|---|---|---|
| ensemble | **0.8555** | 0.5024 | 0.1659 | 0.0145 | 0.605 |
| ensemble (calibrated) | 0.8583 | 0.5035 | 0.1662 | **0.0127** | 0.605 |
| dixon_coles | 0.8644 | 0.5044 | 0.1668 | 0.0130 | 0.604 |
| boosting | 0.8769 | 0.5152 | 0.1712 | 0.0170 | 0.603 |
| elo | 0.8787 | 0.5165 | 0.1711 | 0.0329 | 0.603 |
| poisson | 0.8829 | 0.5182 | 0.1731 | 0.0400 | 0.595 |
| baseline: uniform | 1.0986 | 0.6667 | 0.2392 | 0.1437 | 0.477 |

Every model comfortably beats the uniform baseline. The ensemble is best on the
proper scoring rules; the calibrated ensemble has the best calibration with a
negligible log-loss cost.

**Stability (per-year log loss)** — the ensemble is best or tied-best every year
2021–2026 (2020 is COVID-disrupted and noisy for all models). Full table in
`artifacts/evaluations/backtest_report.md`.

## Baselines
Uniform (1/3,1/3,1/3) is included automatically. The Elo and Poisson models also
serve as informative baselines for the more complex models. Market-consensus
odds are **not** used (not freely/legally available as a clean feed); they are
documented as a future comparison-only reference, never a hidden feature.

## Artifacts
- `artifacts/evaluations/backtest_predictions.parquet` — every out-of-fold prediction.
- `artifacts/evaluations/backtest_summary.json` — metrics, weights, slices.
- `artifacts/evaluations/backtest_report.md` — human-readable report.
- `artifacts/figures/model_comparison.png`, `calibration_curve.png`.

## Reproduce
```bash
make backtest        # or: python scripts/run_backtest.py
```
Deterministic given `WC2026_SEED`.

## Live track record
Separately, `wc2026 freeze` makes genuine **pre-kickoff** predictions for the
World Cup matches already played (model refit per matchday on prior data only)
and scores them — an honest, if small and high-variance, real-world check
(`artifacts/predictions/track_record.json`).
