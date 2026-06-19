"""Proper scoring rules and calibration metrics for 1X2 predictions.

All functions take ``probs`` of shape (n, 3) in [home, draw, away] order and
integer ``y`` in {0, 1, 2}.  These are the metrics used to *select* the final
model (log loss first, then calibration, Brier, RPS — see docs/MODELING.md).
"""
from __future__ import annotations

import numpy as np


def _onehot(y: np.ndarray, k: int = 3) -> np.ndarray:
    o = np.zeros((len(y), k))
    o[np.arange(len(y)), y] = 1.0
    return o


def log_loss_multiclass(probs: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(probs, 1e-12, 1)
    return float(-np.log(p[np.arange(len(y)), y]).mean())


def brier_score(probs: np.ndarray, y: np.ndarray) -> float:
    """Multiclass Brier = mean squared error vs one-hot (range 0..2)."""
    o = _onehot(y, probs.shape[1])
    return float(((probs - o) ** 2).sum(axis=1).mean())


def rps_score(probs: np.ndarray, y: np.ndarray) -> float:
    """Ranked Probability Score for ordinal outcomes home<draw<away."""
    o = _onehot(y, probs.shape[1])
    cp = np.cumsum(probs, axis=1)
    co = np.cumsum(o, axis=1)
    r = probs.shape[1]
    return float(((cp[:, :-1] - co[:, :-1]) ** 2).sum(axis=1).mean() / (r - 1))


def accuracy(probs: np.ndarray, y: np.ndarray) -> float:
    return float((probs.argmax(axis=1) == y).mean())


def confusion_matrix(probs: np.ndarray, y: np.ndarray) -> list[list[int]]:
    pred = probs.argmax(axis=1)
    cm = np.zeros((3, 3), dtype=int)
    for t, p in zip(y, pred, strict=True):
        cm[t, p] += 1
    return [[int(v) for v in row] for row in cm]


def expected_calibration_error(probs: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """Top-label ECE: bins the predicted (max) class confidence vs accuracy."""
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == y).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y)
    for b in range(n_bins):
        mask = (conf > bins[b]) & (conf <= bins[b + 1])
        if mask.sum() == 0:
            continue
        ece += abs(correct[mask].mean() - conf[mask].mean()) * mask.sum() / n
    return float(ece)


def calibration_curve_multiclass(probs: np.ndarray, y: np.ndarray, n_bins: int = 10) -> dict:
    """Reliability data pooled over the 3 one-vs-rest problems."""
    o = _onehot(y, probs.shape[1])
    p = probs.reshape(-1)
    t = o.reshape(-1)
    bins = np.linspace(0, 1, n_bins + 1)
    xs, ys, counts = [], [], []
    for b in range(n_bins):
        mask = (p > bins[b]) & (p <= bins[b + 1])
        if mask.sum() == 0:
            continue
        xs.append(float(p[mask].mean()))
        ys.append(float(t[mask].mean()))
        counts.append(int(mask.sum()))
    return {"mean_predicted": xs, "empirical": ys, "counts": counts}


def evaluate_predictions(probs: np.ndarray, y: np.ndarray) -> dict:
    return {
        "n": int(len(y)),
        "log_loss": log_loss_multiclass(probs, y),
        "brier": brier_score(probs, y),
        "rps": rps_score(probs, y),
        "ece": expected_calibration_error(probs, y),
        "accuracy": accuracy(probs, y),
        "confusion_matrix": confusion_matrix(probs, y),
        "draw_rate_pred": float(probs[:, 1].mean()),
        "draw_rate_actual": float((y == 1).mean()),
    }
