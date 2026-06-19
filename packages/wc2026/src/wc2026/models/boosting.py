"""Gradient-boosting model on engineered features.

Uses scikit-learn's histogram gradient boosting (a LightGBM-style algorithm)
so the project stays pure-Python/reproducible with no compiled native deps.
Rationale and the XGBoost/LightGBM/CatBoost trade-off are documented in
docs/MODELING.md and docs/DECISIONS.md.

Produces 1X2 directly (classifier) and a score matrix via two Poisson-loss
goal regressors, so it satisfies the common interface.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

from wc2026 import features as _features  # module ref avoids a features<->models cycle
from wc2026.config import SEED, EloConfig
from wc2026.models.base import HOME, MatchModel, result_index


class BoostingModel(MatchModel):
    name = "boosting"

    def __init__(self, elo_cfg: EloConfig | None = None, max_goals: int = 10,
                 learning_rate: float = 0.05, max_iter: int = 350, seed: int = SEED):
        self.elo_cfg = elo_cfg or EloConfig()
        self.max_goals = max_goals
        self.lr = learning_rate
        self.max_iter = max_iter
        self.seed = seed
        self.fb: _features.FeatureBuilder | None = None
        self.clf: HistGradientBoostingClassifier | None = None
        self.reg_home: HistGradientBoostingRegressor | None = None
        self.reg_away: HistGradientBoostingRegressor | None = None
        self.classes_: list[int] = [HOME, 1, 2]

    def fit(self, matches: pd.DataFrame) -> BoostingModel:
        self.fb = _features.FeatureBuilder(self.elo_cfg)
        feats = self.fb.build_all(matches)
        X = feats[_features.FEATURE_COLUMNS].to_numpy(dtype=float)
        y = np.array([
            result_index(h, a)
            for h, a in zip(feats["home_score"], feats["away_score"], strict=True)
        ])
        gh = feats["home_score"].to_numpy(dtype=float)
        ga = feats["away_score"].to_numpy(dtype=float)

        common = {
            "learning_rate": self.lr, "max_iter": self.max_iter,
            "max_depth": None, "max_leaf_nodes": 31, "l2_regularization": 1.0,
            "early_stopping": True, "validation_fraction": 0.1,
            "random_state": self.seed,
        }
        self.clf = HistGradientBoostingClassifier(**common)
        self.clf.fit(X, y)
        self.classes_ = list(self.clf.classes_)
        self.reg_home = HistGradientBoostingRegressor(loss="poisson", **common)
        self.reg_away = HistGradientBoostingRegressor(loss="poisson", **common)
        self.reg_home.fit(X, np.clip(gh, 0, None))
        self.reg_away.fit(X, np.clip(ga, 0, None))
        return self

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        X = self.fb.transform(fixtures).to_numpy(dtype=float)
        raw = self.clf.predict_proba(X)
        # remap to fixed [home, draw, away] order regardless of class ordering
        out = np.zeros((len(X), 3))
        for col, cls in enumerate(self.classes_):
            out[:, cls] = raw[:, col]
        return out / out.sum(axis=1, keepdims=True)

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        X = self.fb.transform(fixtures).to_numpy(dtype=float)
        eh = np.clip(self.reg_home.predict(X), 0.05, None)
        ea = np.clip(self.reg_away.predict(X), 0.05, None)
        return np.column_stack([eh, ea])

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        eg = self.predict_expected_goals(fixtures)
        ks = np.arange(self.max_goals + 1)
        return [np.outer(poisson.pmf(ks, eh), poisson.pmf(ks, ea)) for eh, ea in eg]

    def feature_importance(self, fixtures: pd.DataFrame) -> dict[str, float]:
        """Permutation-free proxy: mean |SHAP-like| via predict spread is overkill
        here; expose the classifier's training feature names with gain when
        available, else uniform."""
        # HistGB exposes no native importances; return names for the UI to map.
        return {c: 0.0 for c in _features.FEATURE_COLUMNS}

    def metadata(self) -> dict:
        return {
            "name": self.name, "algorithm": "sklearn HistGradientBoosting",
            "learning_rate": self.lr, "max_iter": self.max_iter,
            "features": _features.FEATURE_COLUMNS,
        }
