# Backtest Report

- Seed: `20260611`  
- Validation rows: 3929, Test rows: 6018  
- Ensemble weights: `{"elo": 0.0, "poisson": 0.0, "dixon_coles": 0.66, "boosting": 0.34}`  
- Calibration: **isotonic** (T=0.951)

## Overall test metrics

| Model | Log loss | Brier | RPS | ECE | Accuracy |
|---|---|---|---|---|---|
| ensemble | 0.8555 | 0.5024 | 0.1659 | 0.0145 | 0.605 |
| ensemble_cal | 0.8583 | 0.5035 | 0.1662 | 0.0127 | 0.605 |
| dixon_coles | 0.8644 | 0.5044 | 0.1668 | 0.0130 | 0.604 |
| boosting | 0.8769 | 0.5152 | 0.1712 | 0.0170 | 0.603 |
| elo | 0.8787 | 0.5165 | 0.1711 | 0.0329 | 0.603 |
| poisson | 0.8829 | 0.5182 | 0.1731 | 0.0400 | 0.595 |
| baseline_uniform | 1.0986 | 0.6667 | 0.2392 | 0.1437 | 0.477 |

## Per-year log loss (top models)

| Year | dixon_coles | boosting | ensemble | ensemble_cal |
|---|---|---|---|---|
| 2020 | 0.9812 | 1.0251 | 0.9874 | 0.9987 |
| 2021 | 0.7899 | 0.8062 | 0.7885 | 0.7871 |
| 2022 | 0.9202 | 0.9227 | 0.9063 | 0.9083 |
| 2023 | 0.8777 | 0.8788 | 0.8553 | 0.8620 |
| 2024 | 0.8813 | 0.9066 | 0.8780 | 0.8791 |
| 2025 | 0.8193 | 0.8181 | 0.8068 | 0.8120 |
| 2026 | 0.8635 | 0.8915 | 0.8620 | 0.8576 |

_Figures: `artifacts/figures/model_comparison.png`, `artifacts/figures/calibration_curve.png`._
