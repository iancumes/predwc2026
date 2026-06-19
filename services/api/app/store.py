"""Artifact-backed data store for the API.

Reads the JSON/Parquet artifacts produced by the wc2026 pipeline (simulation,
frozen predictions, backtest metrics) plus the live tournament structure.  Every
loader degrades gracefully: if an artifact is missing the API still answers and
reports ``demo_mode`` so the frontend can show an "not yet generated" state.
Loaders are cached and invalidated by file mtime, so re-running the pipeline is
picked up without restarting the server.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from wc2026.config import PATHS
from wc2026.data.ingest import load_matches
from wc2026.data.tournament import load_tournament
from wc2026.standings import standings_with_probabilities
from wc2026.teams import confederation, team_code

PRED_DIR = PATHS.artifacts / "predictions"


def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


# --- cached loaders keyed by (path, mtime) so edits invalidate the cache ----
@lru_cache(maxsize=8)
def _sim_cached(_key) -> dict:
    return _read_json(PATHS.simulations / "latest.json", {})


def sim_results() -> dict:
    return _sim_cached(_mtime(PATHS.simulations / "latest.json"))


@lru_cache(maxsize=8)
def _preds_cached(_key) -> list[dict]:
    return _read_json(PRED_DIR / "current.json", [])


def predictions() -> list[dict]:
    return _preds_cached(_mtime(PRED_DIR / "current.json"))


def predictions_by_match() -> dict[str, dict]:
    return {p["match_id"]: p for p in predictions()}


def track_record() -> dict:
    return _read_json(PRED_DIR / "track_record.json", {"n": 0})


def backtest_summary() -> dict:
    return _read_json(PATHS.evaluations / "backtest_summary.json", {})


def model_meta() -> dict:
    return _read_json(PATHS.models / "production_meta.json", {})


@lru_cache(maxsize=2)
def _tournament_cached(_key):
    return load_tournament()


def tournament():
    p = PATHS.data_processed / "matches.parquet"
    return _tournament_cached(_mtime(p))


def status() -> dict:
    t = tournament()
    sim = sim_results()
    return {
        "demo_mode": not (PATHS.simulations / "latest.json").exists(),
        "data_cutoff": model_meta().get("data_cutoff"),
        "model": model_meta().get("name"),
        "model_calibration": model_meta().get("calibration"),
        "n_sims": sim.get("n_sims"),
        "sim_generated_at": sim.get("generated_at"),
        "played_group_matches": int(len(t.played)),
        "pending_group_matches": int(len(t.pending)),
    }


# ---------------------------------------------------------------------------
def teams() -> list[dict]:
    t = tournament()
    sim_rows = {r["team"]: r for r in sim_results().get("teams", [])}
    out = []
    for name in t.teams:
        s = sim_rows.get(name, {})
        out.append({
            "code": team_code(name), "name": name,
            "group": t.group_of(name), "confederation": confederation(name),
            "p_champion": s.get("p_champion"), "p_reach_final": s.get("p_reach_final"),
            "p_win_group": s.get("p_win_group"),
        })
    out.sort(key=lambda r: (r["p_champion"] is None, -(r["p_champion"] or 0)))
    return out


def team_detail(code: str) -> dict | None:
    t = tournament()
    name = next((n for n in t.teams if team_code(n) == code), None)
    if name is None:
        return None
    s = next((r for r in sim_results().get("teams", []) if r["team"] == name), {})
    # recent results for this team
    matches = load_matches(played_only=True)
    mask = (matches["home_team"] == name) | (matches["away_team"] == name)
    recent = matches[mask].sort_values("date").tail(10)
    recent_list = [{
        "date": r["date"].strftime("%Y-%m-%d"), "home": r["home_team"], "away": r["away_team"],
        "score": f"{int(r['home_score'])}-{int(r['away_score'])}", "tournament": r["tournament"],
    } for _, r in recent.iterrows()]
    return {
        "code": code, "name": name, "group": t.group_of(name),
        "confederation": confederation(name), "is_host": name in {"United States", "Mexico", "Canada"},
        "simulation": s, "recent_matches": recent_list,
        "group_fixtures": _group_fixture_rows(t, t.group_of(name)),
    }


def _group_fixture_rows(t, group: str) -> list[dict]:
    preds = predictions_by_match()
    rows = []
    for _, m in t.group_fixtures(group).iterrows():
        p = preds.get(m["match_id"], {})
        rows.append({
            "match_id": m["match_id"], "date": m["date"].strftime("%Y-%m-%d"),
            "home": m["home_team"], "away": m["away_team"], "status": m["status"],
            "home_score": None if m["status"] != "played" else int(m["home_score"]),
            "away_score": None if m["status"] != "played" else int(m["away_score"]),
            "p_home": p.get("home_win_probability"), "p_draw": p.get("draw_probability"),
            "p_away": p.get("away_win_probability"),
        })
    return rows


def matches(group: str | None = None, status_filter: str | None = None,
            team: str | None = None) -> list[dict]:
    t = tournament()
    preds = predictions_by_match()
    out = []
    for _, m in t.fixtures.sort_values("date").iterrows():
        g = t.group_of(m["home_team"])
        if group and g != group:
            continue
        if status_filter and m["status"] != status_filter:
            continue
        if team and team not in (team_code(m["home_team"]), team_code(m["away_team"])):
            continue
        p = preds.get(m["match_id"], {})
        out.append({
            "match_id": m["match_id"], "date": m["date"].strftime("%Y-%m-%d"),
            "group": g, "home": m["home_team"], "away": m["away_team"],
            "home_code": team_code(m["home_team"]), "away_code": team_code(m["away_team"]),
            "status": m["status"], "neutral": bool(m["neutral_venue"]),
            "city": m["city"], "country": m["country"],
            "home_score": None if m["status"] != "played" else int(m["home_score"]),
            "away_score": None if m["status"] != "played" else int(m["away_score"]),
            "p_home": p.get("home_win_probability"), "p_draw": p.get("draw_probability"),
            "p_away": p.get("away_win_probability"),
        })
    return out


def match_detail(match_id: str) -> dict | None:
    t = tournament()
    row = t.fixtures[t.fixtures["match_id"] == match_id]
    if len(row) == 0:
        return None
    m = row.iloc[0]
    pred = predictions_by_match().get(match_id)
    return {
        "match_id": match_id, "date": m["date"].strftime("%Y-%m-%d"),
        "group": t.group_of(m["home_team"]), "home": m["home_team"], "away": m["away_team"],
        "status": m["status"], "neutral": bool(m["neutral_venue"]),
        "city": m["city"], "country": m["country"],
        "home_score": None if m["status"] != "played" else int(m["home_score"]),
        "away_score": None if m["status"] != "played" else int(m["away_score"]),
        "prediction": pred,
    }


def groups() -> dict:
    t = tournament()
    return standings_with_probabilities(t, sim_results().get("teams"))


def bracket() -> dict:
    t = tournament()
    sim_rows = {r["team"]: r for r in sim_results().get("teams", [])}
    return {
        "rounds": t.bracket,
        "round_reach": [
            {"team": n, "code": team_code(n), "group": t.group_of(n),
             "p_reach_r32": sim_rows.get(n, {}).get("p_reach_r32"),
             "p_reach_r16": sim_rows.get(n, {}).get("p_reach_r16"),
             "p_reach_qf": sim_rows.get(n, {}).get("p_reach_qf"),
             "p_reach_sf": sim_rows.get(n, {}).get("p_reach_sf"),
             "p_reach_final": sim_rows.get(n, {}).get("p_reach_final"),
             "p_champion": sim_rows.get(n, {}).get("p_champion")}
            for n in t.teams
        ],
    }


def model_calibration() -> dict:
    """Reliability curve computed from stored backtest predictions (ensemble)."""
    path = PATHS.evaluations / "backtest_predictions.parquet"
    if not path.exists():
        return {"available": False}
    import numpy as np
    import pandas as pd
    from wc2026.evaluation.metrics import calibration_curve_multiclass
    df = pd.read_parquet(path)
    test = df[df["period"] == "test"]
    if len(test) == 0:
        return {"available": False}
    w = backtest_summary().get("ensemble_weights", {})
    names = [n for n in ("elo", "poisson", "dixon_coles", "boosting") if f"{n}__h" in test]
    stack = np.stack([test[[f"{n}__h", f"{n}__d", f"{n}__a"]].to_numpy() for n in names])
    weights = np.array([w.get(n, 1 / len(names)) for n in names])
    ens = np.tensordot(weights, stack, axes=(0, 0))
    ens = ens / ens.sum(axis=1, keepdims=True)
    y = test["outcome"].to_numpy()
    cc = calibration_curve_multiclass(ens, y, n_bins=12)
    return {"available": True, **cc}
