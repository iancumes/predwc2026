"""Ensemble that blends base models with convex weights.

Weights are optimised on a held-out validation split (never the training or test
data) to minimise multiclass log loss, parameterised through a softmax so they
stay on the probability simplex.  Score matrices are blended with the same
weights, keeping 1X2 and exact-score outputs mutually consistent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from wc2026.models.base import MatchModel, normalise_rows


def _logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1)
    return float(-np.log(p[np.arange(len(y)), y]).mean())


class EnsembleModel(MatchModel):
    name = "ensemble"

    def __init__(self, models: dict[str, MatchModel]):
        self.models = models
        self.weights: dict[str, float] = {k: 1 / len(models) for k in models}
        self._order = list(models.keys())

    def fit_weights(self, val_fixtures: pd.DataFrame, y: np.ndarray) -> EnsembleModel:
        preds = np.stack([
            normalise_rows(self.models[k].predict_proba(val_fixtures)) for k in self._order
        ])  # (M, n, 3)

        def loss(raw):
            w = np.exp(raw - raw.max())
            w /= w.sum()
            blended = np.tensordot(w, preds, axes=(0, 0))  # (n,3)
            return _logloss(normalise_rows(blended), y)

        res = minimize(loss, np.zeros(len(self._order)), method="Nelder-Mead",
                       options={"maxiter": 2000, "xatol": 1e-4, "fatol": 1e-6})
        w = np.exp(res.x - res.x.max())
        w /= w.sum()
        self.weights = {k: float(w[i]) for i, k in enumerate(self._order)}
        return self

    def fit(self, matches: pd.DataFrame) -> EnsembleModel:  # pragma: no cover
        for m in self.models.values():
            m.fit(matches)
        return self

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        blended = np.zeros((len(fixtures), 3))
        for k in self._order:
            blended += self.weights[k] * normalise_rows(self.models[k].predict_proba(fixtures))
        return normalise_rows(blended)

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        per_model = {}
        for k in self._order:
            try:
                per_model[k] = self.models[k].predict_score_matrix(fixtures)
            except NotImplementedError:
                continue
        n = len(fixtures)
        out: list[np.ndarray] = []
        wsum = sum(self.weights[k] for k in per_model) or 1.0
        for i in range(n):
            acc = np.zeros_like(next(iter(per_model.values()))[i], dtype=float)
            for k in per_model:
                acc = acc + (self.weights[k] / wsum) * per_model[k][i]
            out.append(acc)
        return out

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        mats = self.predict_score_matrix(fixtures)
        ks = np.arange(mats[0].shape[0])
        out = np.zeros((len(mats), 2))
        for i, m in enumerate(mats):
            mm = m / m.sum()
            out[i] = [(mm.sum(axis=1) * ks).sum(), (mm.sum(axis=0) * ks).sum()]
        return out

    def metadata(self) -> dict:
        return {"name": self.name, "weights": self.weights,
                "members": {k: v.metadata() for k, v in self.models.items()}}
