# Modeling

All models implement one interface (`wc2026.models.base.MatchModel`):
`fit`, `predict_proba` → (n,3) `[home, draw, away]`, `predict_score_matrix`
→ `M[i,j]=P(home i, away j)`, `predict_expected_goals`, `metadata`, `save/load`.
Markets (over/under, BTTS, exact scores) derive from the single score matrix so
1X2 and scoreline outputs are always mutually consistent.

## Models implemented

### Elo (baseline A)
World-Football style. Pre-match rating difference `R_h + HA·home − R_a`;
update `R' = R + K·G·(S − E)` with margin-of-victory multiplier `G` and
tournament-weighted `K`. Online, chronological pass ⇒ the pre-match rating only
sees the past (leakage-free). Elo→goals: two small fitted regressions
(supremacy ∝ Elo diff; total goals ∝ |Elo diff|) feed an independent-Poisson
score matrix, so Elo yields consistent 1X2 **and** scorelines.

### Poisson GLM (baseline B)
`log E[goals] = intercept + attack[scorer] − defence[conceder] + home·is_home`,
fit as one Poisson GLM (two rows per match) with exponential time-decay sample
weights; L2 resolves the attack/defence translation degeneracy.

### Dixon–Coles (model C) — strongest single model
Bivariate Poisson with the low-score dependence correction `τ(x,y;λ,μ,ρ)` and
exponential time decay. Penalised MLE via L-BFGS-B with an **analytic gradient**
(verified against `scipy.check_grad`, error ≈ 7e-4), so the ~500-parameter fit
takes <1s and can be refit every backtest fold. Attack constrained to sum to
zero for identifiability; small ridge prior stabilises rarely-seen teams.

### Gradient boosting (model D)
scikit-learn histogram gradient boosting (LightGBM-style) on engineered features
(Elo, recent form PPG, goals for/against, rest days, neutrality, importance).
A classifier gives 1X2; two Poisson-loss regressors give expected goals → score
matrix. *Choice:* histogram GBM keeps the project pure-Python and reproducible
with no compiled native deps; XGBoost/LightGBM/CatBoost are documented
alternatives (see DECISIONS) that did not beat the ensemble enough to justify
the dependency.

### Ensemble (model E) + calibration
Convex blend of the base models, weights learned by minimising validation log
loss on the simplex (softmax-parameterised). The blended 1X2 is then calibrated
— **none vs temperature vs isotonic**, chosen by validation log loss with Occam
margins and isotonic smoothing for out-of-sample robustness. The deployed
`ProductionModel` is this calibrated ensemble.

## Feature engineering (`features.py`)
Computed in one chronological pass (strict `as_of`): pre-match Elo and Elo diff,
exponentially-weighted recent form (PPG, GF, GA over last ~10), rest days,
neutrality, host flag, tournament importance. Adding/removing future matches
cannot change a past match's features (enforced by `tests/test_leakage.py`).

## Model selection criteria (priority order)
1. Out-of-sample **log loss**  2. **Calibration** (ECE)  3. Brier  4. RPS
5. Stability across periods  6. Draw performance  7. Interpretability
8. Operational complexity  9. Accuracy.

Result: the **calibrated ensemble** wins log loss (0.8555 raw / 0.8583
calibrated) and best calibration (ECE 0.0127). Dixon–Coles is a very close,
simpler runner-up (0.8644) and is the dominant ensemble component (weight 0.66).
Elo/Poisson are retained as baselines but receive ~0 ensemble weight (dominated).
See [VALIDATION.md](VALIDATION.md) and [DECISIONS.md](DECISIONS.md).
