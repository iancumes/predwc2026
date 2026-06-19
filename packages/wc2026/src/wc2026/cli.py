"""Command-line interface: `wc2026 <command>`.

Commands: ingest, train, backtest, simulate, freeze, report, info.
Everything is reproducible (seeded) and writes artifacts under artifacts/.
"""
from __future__ import annotations

import argparse
import json
import pickle
import warnings

warnings.filterwarnings("ignore")


from wc2026.config import N_SIMS, PATHS, SEED


def _load_backtest_weights() -> dict | None:
    path = PATHS.evaluations / "backtest_summary.json"
    if path.exists():
        try:
            return json.loads(path.read_text()).get("ensemble_weights")
        except Exception:
            return None
    return None


def cmd_ingest(args) -> None:
    from wc2026.data.ingest import ingest
    ingest()


def cmd_info(args) -> None:
    from wc2026.data.ingest import load_matches
    from wc2026.data.tournament import load_tournament
    m = load_matches()
    t = load_tournament()
    print(f"matches: {len(m)} ({m['date'].min().date()}..{m['date'].max().date()})")
    print(f"played: {(m['status']=='played').sum()} | scheduled: {(m['status']!='played').sum()}")
    print(f"WC2026: {len(t.groups)} groups, {len(t.teams)} teams, "
          f"{len(t.played)} played / {len(t.pending)} pending group matches")
    warns = t.validate()
    print("integrity:", "OK" if not warns else f"{len(warns)} warnings: {warns[:3]}")


def cmd_train(args) -> None:
    from wc2026.data.ingest import load_matches
    from wc2026.models.production import ProductionModel, default_base_models
    PATHS.ensure()
    m = load_matches()
    weights = _load_backtest_weights()
    print(f"[train] fitting production ensemble (seed={SEED}); "
          f"weights={'from backtest' if weights else 'learned on validation'}")
    model = ProductionModel(base_models=default_base_models(boosting_iter=args.boosting_iter),
                            fixed_weights=weights)
    model.fit(m)
    with (PATHS.models / "production.pkl").open("wb") as fh:
        pickle.dump(model, fh)
    meta = model.metadata()
    meta["seed"] = SEED
    (PATHS.models / "production_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"[train] saved {PATHS.models/'production.pkl'}")
    print(f"[train] weights={meta['weights']} calibration={meta['calibration']}")


def cmd_backtest(args) -> None:
    import runpy
    script = PATHS.root / "scripts" / "run_backtest.py"
    runpy.run_path(str(script), run_name="__main__")


def cmd_export(args) -> None:
    """Materialise every API response as static JSON for a backend-free deploy."""
    import runpy
    script = PATHS.root / "scripts" / "export_static.py"
    runpy.run_path(str(script), run_name="__main__")


def _load_or_fit_model(boosting_iter: int = 250):
    from wc2026.data.ingest import load_matches
    from wc2026.models.production import ProductionModel, default_base_models
    path = PATHS.models / "production.pkl"
    if path.exists():
        with path.open("rb") as fh:
            return pickle.load(fh)
    print("[model] no saved production model; fitting now...")
    weights = _load_backtest_weights()
    m = load_matches()
    return ProductionModel(base_models=default_base_models(boosting_iter=boosting_iter),
                           fixed_weights=weights).fit(m)


def cmd_simulate(args) -> None:
    from wc2026.data.tournament import load_tournament
    from wc2026.simulation import WorldCupSimulator
    PATHS.ensure()
    model = _load_or_fit_model()
    t = load_tournament()
    sim = WorldCupSimulator(t, model, n_sims=args.n_sims, seed=args.seed)
    print(f"[simulate] running {args.n_sims} Monte Carlo simulations (seed={args.seed})...")
    res = sim.run(save=True)
    print(f"[simulate] saved {PATHS.simulations/'latest.json'}")
    print("\nTop 10 title favourites:")
    print(res.team_table.head(10)[["team", "group", "p_reach_qf",
          "p_reach_final", "p_champion"]].to_string(index=False))


def cmd_freeze(args) -> None:
    from wc2026.data.ingest import load_matches
    from wc2026.data.tournament import load_tournament
    from wc2026.models.production import ProductionModel, default_base_models
    from wc2026.predictions import freeze_world_cup
    PATHS.ensure()
    m = load_matches()
    t = load_tournament()
    weights = _load_backtest_weights()
    factory = lambda: ProductionModel(  # noqa: E731
        base_models=default_base_models(boosting_iter=args.boosting_iter),
        fixed_weights=weights)
    freeze_world_cup(m, t, model_factory=factory)


def cmd_report(args) -> None:
    """Assemble a consolidated status report from saved artifacts."""
    out: dict[str, object] = {"seed": SEED}
    bt = PATHS.evaluations / "backtest_summary.json"
    sim = PATHS.simulations / "latest.json"
    tr = PATHS.artifacts / "predictions" / "track_record.json"
    if bt.exists():
        s = json.loads(bt.read_text())
        out["backtest"] = {"n_test": s["n_test"], "calibration": s["calibration_method"],
                           "best": min(s["overall"].items(), key=lambda kv: kv[1]["log_loss"])[0],
                           "overall": {k: round(v["log_loss"], 4) for k, v in s["overall"].items()}}
    if sim.exists():
        s = json.loads(sim.read_text())
        out["simulation"] = {"n_sims": s["n_sims"],
                             "top5": [(t["team"], round(t["p_champion"], 4)) for t in s["teams"][:5]]}
    if tr.exists():
        out["track_record"] = json.loads(tr.read_text())
    (PATHS.artifacts / "status_report.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="wc2026", description="FIFA World Cup 2026 predictor")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest", help="download/normalise/validate match data")
    sub.add_parser("info", help="show data + tournament status")
    sub.add_parser("backtest", help="walk-forward model comparison")
    sub.add_parser("report", help="consolidated status report")
    sub.add_parser("export", help="write static JSON for the web app (backend-free deploy)")

    pt = sub.add_parser("train", help="fit & save the production model")
    pt.add_argument("--boosting-iter", type=int, default=250)

    ps = sub.add_parser("simulate", help="Monte Carlo tournament simulation")
    ps.add_argument("--n-sims", type=int, default=N_SIMS)
    ps.add_argument("--seed", type=int, default=SEED)

    pf = sub.add_parser("freeze", help="freeze versioned match predictions")
    pf.add_argument("--boosting-iter", type=int, default=180)

    args = p.parse_args(argv)
    {
        "ingest": cmd_ingest, "info": cmd_info, "train": cmd_train,
        "backtest": cmd_backtest, "simulate": cmd_simulate,
        "freeze": cmd_freeze, "report": cmd_report, "export": cmd_export,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
