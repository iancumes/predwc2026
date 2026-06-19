"""Strictly temporal walk-forward backtesting and model comparison.

Timeline:  train (< val_start) | validation [val_start, test_start) | test [test_start, end)

* Base models are **refit every fold** on data strictly before the fold and used
  to predict that fold only (no random splits, no future leakage).
* Ensemble weights and the probability calibrator are learned **only on the
  validation predictions**, then applied unchanged to the test folds — so meta
  parameters never see test outcomes.
* Metrics are reported on the test period, overall and sliced by year,
  confederation, neutrality and favourite strength.
"""
from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from wc2026.config import PATHS
from wc2026.evaluation.metrics import evaluate_predictions
from wc2026.models.base import MatchModel, normalise_rows, result_index
from wc2026.models.calibration import _Calibrator

ModelFactory = Callable[[], MatchModel]


def _date_folds(start, end, step_days):
    folds, t = [], pd.Timestamp(start)
    end = pd.Timestamp(end)
    while t < end:
        nxt = t + pd.Timedelta(days=step_days)
        folds.append((t, min(nxt, end)))
        t = nxt
    return folds


def run_backtest(
    matches: pd.DataFrame,
    factories: dict[str, ModelFactory],
    val_start: str = "2017-01-01",
    test_start: str = "2021-01-01",
    test_end: str = "2026-06-10",
    step_days: int = 180,
    verbose: bool = True,
) -> pd.DataFrame:
    """Walk-forward predict every fold with every base model. Returns long frame."""
    played = matches[matches["status"] == "played"].copy()
    folds = _date_folds(val_start, test_end, step_days)
    records = []

    for fi, (f0, f1) in enumerate(folds):
        train = played[played["date"] < f0]
        fold = played[(played["date"] >= f0) & (played["date"] < f1)]
        if len(fold) == 0 or len(train) < 500:
            continue
        y = np.array([result_index(h, a) for h, a in
                      zip(fold["home_score"], fold["away_score"], strict=True)])
        period = "val" if f0 < pd.Timestamp(test_start) else "test"

        fold_probs = {}
        for name, factory in factories.items():
            model = factory().fit(train)
            fold_probs[name] = normalise_rows(model.predict_proba(fold))

        for k in range(len(fold)):
            row = fold.iloc[k]
            base = {
                "fold": fi, "period": period, "date": row["date"],
                "home_team": row["home_team"], "away_team": row["away_team"],
                "home_conf": row["confederation_home"], "away_conf": row["confederation_away"],
                "neutral": bool(row["neutral_venue"]), "is_world_cup": bool(row["is_world_cup"]),
                "outcome": int(y[k]),
            }
            for name in factories:
                p = fold_probs[name][k]
                base[f"{name}__h"] = p[0]
                base[f"{name}__d"] = p[1]
                base[f"{name}__a"] = p[2]
            records.append(base)
        if verbose:
            print(f"[backtest] fold {fi+1}/{len(folds)} {f0.date()}..{f1.date()} "
                  f"({period}) n={len(fold)} train={len(train)}")

    preds = pd.DataFrame.from_records(records)
    PATHS.evaluations.mkdir(parents=True, exist_ok=True)
    preds.to_parquet(PATHS.evaluations / "backtest_predictions.parquet", index=False)
    return preds


def _probs(preds: pd.DataFrame, name: str) -> np.ndarray:
    return preds[[f"{name}__h", f"{name}__d", f"{name}__a"]].to_numpy()


def _optimize_weights(stack: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Convex weights (softmax-parameterised) minimising log loss. stack=(M,n,3)."""
    M = stack.shape[0]

    def loss(raw):
        w = np.exp(raw - raw.max()); w /= w.sum()
        blended = np.tensordot(w, stack, axes=(0, 0))
        p = np.clip(blended, 1e-12, 1)
        return float(-np.log(p[np.arange(len(y)), y]).mean())

    res = minimize(loss, np.zeros(M), method="Nelder-Mead",
                   options={"maxiter": 3000, "xatol": 1e-4, "fatol": 1e-7})
    w = np.exp(res.x - res.x.max()); w /= w.sum()
    return w


def summarize_backtest(preds: pd.DataFrame, base_names: list[str]) -> dict:
    """Fit ensemble + calibration on val, evaluate everything on test, with slices."""
    val = preds[preds["period"] == "val"]
    test = preds[preds["period"] == "test"]
    if len(test) == 0:
        test = preds  # degenerate (tiny) configs: evaluate on whatever we have
    yv = val["outcome"].to_numpy() if len(val) else test["outcome"].to_numpy()
    yt = test["outcome"].to_numpy()

    # ----- ensemble weights + calibrators learned on validation -----
    val_stack = np.stack([_probs(val if len(val) else test, n) for n in base_names])
    weights = _optimize_weights(val_stack, yv)
    weight_map = {n: float(weights[i]) for i, n in enumerate(base_names)}

    def ensemble(p: pd.DataFrame) -> np.ndarray:
        s = np.stack([_probs(p, n) for n in base_names])
        return normalise_rows(np.tensordot(weights, s, axes=(0, 0)))

    # calibrate the ensemble (best of none/temperature/isotonic on val)
    cal = _Calibrator().fit(ensemble(val) if len(val) else ensemble(test), yv)

    # ----- assemble per-model test predictions -----
    model_test_probs = {n: _probs(test, n) for n in base_names}
    model_test_probs["ensemble"] = ensemble(test)
    model_test_probs["ensemble_cal"] = cal.transform(ensemble(test))

    overall = {n: evaluate_predictions(p, yt) for n, p in model_test_probs.items()}

    # ----- slices for the chosen reporting model set -----
    def slice_metrics(mask: np.ndarray) -> dict:
        if mask.sum() < 20:
            return {}
        return {n: evaluate_predictions(p[mask], yt[mask])
                for n, p in model_test_probs.items()}

    slices: dict[str, dict] = {}
    years = test["date"].dt.year.to_numpy()
    for yr in sorted(set(years.tolist())):
        slices[f"year_{yr}"] = slice_metrics(years == yr)
    slices["neutral"] = slice_metrics(test["neutral"].to_numpy())
    slices["non_neutral"] = slice_metrics(~test["neutral"].to_numpy())
    slices["world_cup"] = slice_metrics(test["is_world_cup"].to_numpy())
    for conf in ("UEFA", "CONMEBOL", "CAF", "AFC", "CONCACAF"):
        m = (test["home_conf"] == conf).to_numpy() | (test["away_conf"] == conf).to_numpy()
        slices[f"conf_{conf}"] = slice_metrics(m)
    # favourite strength buckets (by ensemble max prob)
    fav = model_test_probs["ensemble_cal"].max(axis=1)
    slices["favourite_strong>0.6"] = slice_metrics(fav > 0.6)
    slices["favourite_close<=0.45"] = slice_metrics(fav <= 0.45)

    # ----- baselines: uniform & Elo-favourite (no-draw) -----
    uniform = np.full((len(yt), 3), 1 / 3)
    overall["baseline_uniform"] = evaluate_predictions(uniform, yt)

    summary = {
        "n_val": int(len(val)), "n_test": int(len(yt)),
        "ensemble_weights": weight_map,
        "calibration_method": cal.method,
        "calibration_temperature": cal.temperature,
        "overall": overall,
        "slices": {k: v for k, v in slices.items() if v},
    }
    PATHS.evaluations.mkdir(parents=True, exist_ok=True)
    (PATHS.evaluations / "backtest_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary
