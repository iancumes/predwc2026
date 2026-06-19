"""Production model: calibrated ensemble used for deployed predictions & sim.

Self-contained — `fit(matches)` trains the base models on the supplied history,
then learns ensemble weights and a probability calibrator on the most recent
slice of that same history (a validation window strictly *before* anything it
will predict).  The honest out-of-sample numbers come from the walk-forward
backtest; this calibrator is fit on recent data so deployed probabilities are
well-behaved.  Optionally accepts fixed weights from the backtest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from wc2026.config import SEED
from wc2026.models.base import MatchModel, result_index
from wc2026.models.boosting import BoostingModel
from wc2026.models.calibration import _Calibrator
from wc2026.models.dixon_coles import DixonColesModel
from wc2026.models.elo import EloModel
from wc2026.models.ensemble import EnsembleModel
from wc2026.models.poisson import PoissonModel


def default_base_models(boosting_iter: int = 250) -> dict[str, MatchModel]:
    return {
        "elo": EloModel(),
        "poisson": PoissonModel(),
        "dixon_coles": DixonColesModel(min_train_date="2008-01-01"),
        "boosting": BoostingModel(max_iter=boosting_iter),
    }


class ProductionModel(MatchModel):
    name = "production_ensemble"

    def __init__(self, base_models: dict[str, MatchModel] | None = None,
                 val_months: int = 24, fixed_weights: dict[str, float] | None = None,
                 seed: int = SEED):
        self.base = base_models or default_base_models()
        self.val_months = val_months
        self.fixed_weights = fixed_weights
        self.seed = seed
        self.ensemble: EnsembleModel | None = None
        self.cal = _Calibrator()
        self.data_cutoff: pd.Timestamp | None = None

    def fit(self, matches: pd.DataFrame) -> ProductionModel:
        played = matches[matches["status"] == "played"].copy()
        self.data_cutoff = played["date"].max()
        for mdl in self.base.values():
            mdl.fit(played)
        self.ensemble = EnsembleModel(self.base)

        val_cut = self.data_cutoff - pd.DateOffset(months=self.val_months)
        val = played[played["date"] >= val_cut]
        if len(val) < 200:
            val = played.tail(500)
        yv = np.array([result_index(h, a) for h, a in
                       zip(val["home_score"], val["away_score"], strict=True)])

        if self.fixed_weights:
            self.ensemble.weights = {k: self.fixed_weights.get(k, 0.0) for k in self.base}
            s = sum(self.ensemble.weights.values()) or 1.0
            self.ensemble.weights = {k: v / s for k, v in self.ensemble.weights.items()}
        else:
            self.ensemble.fit_weights(val, yv)

        self.cal.fit(self.ensemble.predict_proba(val), yv)
        return self

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self.cal.transform(self.ensemble.predict_proba(fixtures))

    def predict_score_matrix(self, fixtures: pd.DataFrame):
        return self.ensemble.predict_score_matrix(fixtures)

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self.ensemble.predict_expected_goals(fixtures)

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "weights": None if self.ensemble is None else self.ensemble.weights,
            "calibration": self.cal.method,
            "temperature": self.cal.temperature,
            "data_cutoff": None if self.data_cutoff is None else self.data_cutoff.strftime("%Y-%m-%d"),
            "base_models": {k: v.name for k, v in self.base.items()},
        }
