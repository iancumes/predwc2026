"""Probability calibration for 1X2 outputs.

Compares *no calibration*, *temperature scaling* (one global T on the log-probs)
and *isotonic regression* (one-vs-rest per class, then renormalised), and keeps
whichever gives the lowest log loss on the held-out calibration split.  Only the
1X2 head is calibrated; score matrices pass through from the base model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression

from wc2026.models.base import MatchModel, normalise_rows


def _logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1)
    return float(-np.log(p[np.arange(len(y)), y]).mean())


class _Calibrator:
    # smoothing mixes a little uniform mass into isotonic outputs so a single
    # over-confident bin cannot blow up out-of-sample log loss.
    ISO_SMOOTH = 0.01
    # Occam margins: only adopt a more complex method if it beats the simpler
    # one on validation by at least this much (guards against val overfitting).
    MARGIN_TEMP = 2e-3
    MARGIN_ISO = 5e-3

    def __init__(self):
        self.method = "none"
        self.temperature = 1.0
        self.iso: list[IsotonicRegression] = []

    def fit(self, probs: np.ndarray, y: np.ndarray) -> _Calibrator:
        probs = normalise_rows(probs)
        ll_none = _logloss(probs, y)

        # temperature scaling on log-probabilities
        logp = np.log(np.clip(probs, 1e-12, 1))

        def temp_ll(t):
            scaled = logp / t
            scaled -= scaled.max(axis=1, keepdims=True)
            ep = np.exp(scaled)
            ep /= ep.sum(axis=1, keepdims=True)
            return _logloss(ep, y)

        res = minimize_scalar(temp_ll, bounds=(0.3, 5.0), method="bounded")
        t_opt = float(res.x)
        ll_temp = temp_ll(t_opt)

        # isotonic one-vs-rest (with smoothing applied before scoring)
        isos = []
        for k in range(3):
            ir = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
            ir.fit(probs[:, k], (y == k).astype(float))
            isos.append(ir)
        self.iso = isos
        ll_iso = _logloss(self._apply_iso(probs), y)

        # Occam selection with margins
        method, best = "none", ll_none
        if ll_temp < best - self.MARGIN_TEMP:
            method, best = "temperature", ll_temp
        if ll_iso < best - self.MARGIN_ISO:
            method = "isotonic"

        self.method = method
        self.temperature = t_opt
        self._scores = {"none": ll_none, "temperature": ll_temp, "isotonic": ll_iso}
        return self

    def _apply_iso(self, probs: np.ndarray) -> np.ndarray:
        cal = np.column_stack([self.iso[k].predict(probs[:, k]) for k in range(3)])
        cal = normalise_rows(cal)
        return normalise_rows((1 - self.ISO_SMOOTH) * cal + self.ISO_SMOOTH / 3)

    def transform(self, probs: np.ndarray) -> np.ndarray:
        probs = normalise_rows(probs)
        if self.method == "none":
            return probs
        if self.method == "temperature":
            logp = np.log(np.clip(probs, 1e-12, 1)) / self.temperature
            logp -= logp.max(axis=1, keepdims=True)
            ep = np.exp(logp)
            return ep / ep.sum(axis=1, keepdims=True)
        return self._apply_iso(probs)  # isotonic (smoothed)


class CalibratedModel(MatchModel):
    """Wrap a fitted base model with a fitted probability calibrator."""

    def __init__(self, base: MatchModel, calibrator: _Calibrator):
        self.base = base
        self.cal = calibrator
        self.name = f"{base.name}+cal:{calibrator.method}"

    @classmethod
    def fit_calibrator(cls, base: MatchModel, cal_fixtures: pd.DataFrame,
                       y: np.ndarray) -> CalibratedModel:
        probs = base.predict_proba(cal_fixtures)
        calibrator = _Calibrator().fit(probs, y)
        return cls(base, calibrator)

    def fit(self, matches: pd.DataFrame) -> CalibratedModel:  # pragma: no cover
        self.base.fit(matches)
        return self

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self.cal.transform(self.base.predict_proba(fixtures))

    def predict_score_matrix(self, fixtures: pd.DataFrame):
        return self.base.predict_score_matrix(fixtures)

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self.base.predict_expected_goals(fixtures)

    def metadata(self) -> dict:
        return {"name": self.name, "calibration": self.cal.method,
                "temperature": self.cal.temperature, "base": self.base.metadata()}
