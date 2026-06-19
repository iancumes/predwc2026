# Backtest Report

- Seed: `20260611`  
- Validation rows: 3929, Test rows: 6018  
- Ensemble weights: `{"elo": 0.0, "poisson": 0.0, "dixon_coles": 0.622, "boosting": 0.378}`  
- Calibration: **isotonic** (T=0.944)

## Overall test metrics

| Model | Log loss | Brier | RPS | ECE | Accuracy |
|---|---|---|---|---|---|
| ensemble | 0.8542 | 0.5018 | 0.1657 | 0.0112 | 0.608 |
| ensemble_cal | 0.8585 | 0.5036 | 0.1664 | 0.0095 | 0.606 |
| dixon_coles | 0.8644 | 0.5044 | 0.1668 | 0.0130 | 0.604 |
| boosting | 0.8703 | 0.5115 | 0.1699 | 0.0101 | 0.602 |
| elo | 0.8787 | 0.5165 | 0.1711 | 0.0329 | 0.603 |
| poisson | 0.8829 | 0.5182 | 0.1731 | 0.0398 | 0.596 |
| baseline_uniform | 1.0986 | 0.6667 | 0.2392 | 0.1437 | 0.477 |

## Per-year log loss (top models)

| Year | dixon_coles | boosting | ensemble | ensemble_cal |
|---|---|---|---|---|
| 2020 | 0.9812 | 0.9945 | 0.9794 | 0.9916 |
| 2021 | 0.7899 | 0.7954 | 0.7858 | 0.7875 |
| 2022 | 0.9202 | 0.9221 | 0.9070 | 0.9122 |
| 2023 | 0.8777 | 0.8688 | 0.8517 | 0.8589 |
| 2024 | 0.8813 | 0.9039 | 0.8793 | 0.8796 |
| 2025 | 0.8193 | 0.8193 | 0.8071 | 0.8145 |
| 2026 | 0.8635 | 0.8779 | 0.8596 | 0.8576 |

_Figures: `artifacts/figures/model_comparison.png`, `artifacts/figures/calibration_curve.png`._
