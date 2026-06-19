# Research

Survey informing the model and data choices. Consulted 2026-06-18.

## Statistical / ML approaches reviewed
- **Elo / Glicko** — simple, robust, well-calibrated rating systems; Elo chosen
  as a baseline and as a feature source. Glicko's rating-uncertainty adds little
  over time-decayed Elo for this use; deferred.
- **Independent Poisson / Poisson regression** — standard goal model; included as
  baseline B.
- **Dixon–Coles (1997)** — bivariate Poisson with low-score correction and time
  decay; the field standard for football scorelines. Adopted as model C and the
  dominant ensemble component.
- **Bivariate/hierarchical Bayesian Poisson** — strong but heavier to fit/operate;
  the penalised-MLE Dixon–Coles captures most of the benefit at a fraction of the
  cost. Deferred.
- **Boosting (XGBoost/LightGBM/CatBoost) & stacking** — flexible on engineered
  features; we use scikit-learn histogram GBM (LightGBM-style) for reproducibility.
- **Neural nets** — not justified by the data volume/quality; deferred.
- **Calibration** — Platt/temperature/isotonic compared; the platform picks the
  most robust per validation.

## Evaluation methodology reviewed
Proper scoring rules (log loss, Brier, RPS) over accuracy; Expected Calibration
Error and reliability curves; strictly temporal walk-forward backtesting and
leakage control. All adopted (see VALIDATION.md).

## Reference repositories evaluated
| Repo | License | Use here |
|---|---|---|
| martj42/international_results | CC0 | **Primary data source** |
| jfjelstul/worldcup | MIT | Historical WC reference (validation of structure) |
| martineastwood/penaltyblog | MIT | Reference for Dixon–Coles/Poisson implementations (ideas only; our code is original) |
| statsbomb/open-data | CC-BY-NC (non-commercial) | Candidate enrichment; not used to keep licensing clean |
| Hicruben/world-cup-2026-prediction-model | check upstream | Reviewed for approach; not copied |
| TopTrenDev/FIFA-World-Cup-2026-Prediction-Market | check upstream | Reviewed; not copied |

No incompatible code was copied. Ideas (Dixon–Coles formulation, time decay,
walk-forward) are standard and independently implemented here.

## Conclusion
A calibrated ensemble of Dixon–Coles + histogram boosting, selected by
out-of-sample log loss and calibration, gives the best accuracy/robustness/
operability trade-off — preferring the simpler Dixon–Coles when it ties.
