#!/usr/bin/env python
"""Run the full walk-forward backtest, write metrics + figures + markdown report."""
from __future__ import annotations

import json
import warnings

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from wc2026.config import PATHS, SEED
from wc2026.data.ingest import load_matches
from wc2026.evaluation.backtest import _probs, run_backtest, summarize_backtest
from wc2026.evaluation.metrics import calibration_curve_multiclass
from wc2026.models import BoostingModel, DixonColesModel, EloModel, PoissonModel

FACTORIES = {
    "elo": lambda: EloModel(),
    "poisson": lambda: PoissonModel(),
    "dixon_coles": lambda: DixonColesModel(min_train_date="2008-01-01"),
    "boosting": lambda: BoostingModel(max_iter=200),
}


def main() -> None:
    PATHS.ensure()
    matches = load_matches()
    print(f"[backtest] loaded {len(matches)} matches; seed={SEED}")

    preds = run_backtest(
        matches, FACTORIES,
        val_start="2016-01-01", test_start="2020-01-01",
        test_end="2026-06-10", step_days=180,
    )
    summary = summarize_backtest(preds, list(FACTORIES))

    # ---- console table ----
    print(f"\n=== TEST metrics (n={summary['n_test']}, val n={summary['n_val']}) ===")
    print(f"ensemble weights: { {k: round(v,3) for k,v in summary['ensemble_weights'].items()} }")
    print(f"calibration: {summary['calibration_method']} (T={summary['calibration_temperature']:.3f})")
    rows = sorted(summary["overall"].items(), key=lambda kv: kv[1]["log_loss"])
    print(f"\n{'model':18s} {'logloss':>8s} {'brier':>7s} {'rps':>7s} {'ece':>6s} {'acc':>6s}")
    for n, m in rows:
        print(f"{n:18s} {m['log_loss']:8.4f} {m['brier']:7.4f} {m['rps']:7.4f} "
              f"{m['ece']:6.4f} {m['accuracy']:6.3f}")

    # ---- figure 1: model comparison ----
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [n for n, _ in rows]
    lls = [m["log_loss"] for _, m in rows]
    colors = ["#16a34a" if n in ("ensemble", "ensemble_cal") else
              ("#9ca3af" if n.startswith("baseline") else "#2563eb") for n in names]
    ax.barh(names[::-1], lls[::-1], color=colors[::-1])
    ax.set_xlabel("Log loss (lower is better)")
    ax.set_title("Walk-forward backtest — model comparison (test period)")
    fig.tight_layout()
    fig.savefig(PATHS.figures / "model_comparison.png", dpi=120)
    plt.close(fig)

    # ---- figure 2: reliability diagram (ensemble_cal vs ensemble) ----
    test = preds[preds["period"] == "test"]
    yt = test["outcome"].to_numpy()
    from wc2026.models.base import normalise_rows
    w = np.array([summary["ensemble_weights"][n] for n in FACTORIES])
    stack = np.stack([_probs(test, n) for n in FACTORIES])
    ens = normalise_rows(np.tensordot(w, stack, axes=(0, 0)))
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    cc = calibration_curve_multiclass(ens, yt, n_bins=12)
    ax.plot(cc["mean_predicted"], cc["empirical"], "o-", color="#16a34a", label="ensemble")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Empirical frequency")
    ax.set_title("Reliability diagram (pooled 1X2, test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PATHS.figures / "calibration_curve.png", dpi=120)
    plt.close(fig)

    # ---- markdown report ----
    lines = ["# Backtest Report", "",
             f"- Seed: `{SEED}`  ",
             f"- Validation rows: {summary['n_val']}, Test rows: {summary['n_test']}  ",
             f"- Ensemble weights: `{json.dumps({k: round(v,3) for k,v in summary['ensemble_weights'].items()})}`  ",
             f"- Calibration: **{summary['calibration_method']}** (T={summary['calibration_temperature']:.3f})",
             "", "## Overall test metrics", "",
             "| Model | Log loss | Brier | RPS | ECE | Accuracy |",
             "|---|---|---|---|---|---|"]
    for n, m in rows:
        lines.append(f"| {n} | {m['log_loss']:.4f} | {m['brier']:.4f} | {m['rps']:.4f} "
                     f"| {m['ece']:.4f} | {m['accuracy']:.3f} |")
    lines += ["", "## Per-year log loss (top models)", "",
              "| Year | " + " | ".join(["dixon_coles", "boosting", "ensemble", "ensemble_cal"]) + " |",
              "|---|---|---|---|---|"]
    for k, v in summary["slices"].items():
        if k.startswith("year_") and v:
            cells = [f"{v.get(mm,{}).get('log_loss', float('nan')):.4f}" for mm in
                     ["dixon_coles", "boosting", "ensemble", "ensemble_cal"]]
            lines.append(f"| {k.replace('year_','')} | " + " | ".join(cells) + " |")
    lines += ["", "_Figures: `artifacts/figures/model_comparison.png`, "
              "`artifacts/figures/calibration_curve.png`._", ""]
    (PATHS.evaluations / "backtest_report.md").write_text("\n".join(lines))
    print(f"\n[backtest] wrote {PATHS.evaluations/'backtest_report.md'} and figures.")


if __name__ == "__main__":
    main()
