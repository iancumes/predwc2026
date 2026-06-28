"""Frozen, versioned, auditable match predictions.

A prediction is generated using only data available *before* kickoff and then
frozen: the store is append-only, keyed by (match_id, model_version_id), so a
prediction is never silently rewritten.  For already-played World Cup matches we
refit the model per matchday (train on matches strictly before that date), which
yields a genuine pre-match prediction and therefore an honest track record.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from wc2026.config import PATHS
from wc2026.data.tournament import Tournament
from wc2026.models.base import MatchModel, market_probabilities, result_index
from wc2026.models.production import ProductionModel
from wc2026.teams import HOSTS_2026

ModelFactory = Callable[[], MatchModel]
STORE = PATHS.artifacts / "predictions"


def model_version_id(model: MatchModel, data_cutoff: pd.Timestamp) -> str:
    meta = json.dumps(model.metadata(), sort_keys=True, default=str)
    raw = f"{model.name}|{meta}|cutoff={data_cutoff.strftime('%Y-%m-%d')}".encode()
    return f"{model.name}-{hashlib.sha1(raw).hexdigest()[:10]}"


def _explain(model: MatchModel, fx_row: pd.Series, eg: tuple[float, float]) -> dict:
    """Honest, model-derived factors (no causal claims)."""
    factors = {
        "expected_home_goals": round(float(eg[0]), 2),
        "expected_away_goals": round(float(eg[1]), 2),
        "neutral_venue": bool(fx_row["neutral_venue"]),
        "home_is_host": fx_row["home_team"] in HOSTS_2026,
        "away_is_host": fx_row["away_team"] in HOSTS_2026,
    }
    # Elo difference if the model exposes an Elo base
    elo = getattr(model, "ensemble", None)
    elo = elo.models.get("elo") if elo is not None else (model if model.name == "elo" else None)
    if elo is not None and hasattr(elo, "engine"):
        rh = elo.engine.get(fx_row["home_team"])
        ra = elo.engine.get(fx_row["away_team"])
        factors["elo_home"] = round(rh, 1)
        factors["elo_away"] = round(ra, 1)
        factors["elo_diff"] = round(rh - ra, 1)
    return factors


def _scorer_rows(scorer_model, fx: pd.Series, mp) -> list[dict]:
    """Anytime-scorer probabilities for both sides (empty if no model/data)."""
    if scorer_model is None:
        return []
    home = scorer_model.scorers(fx["home_team"], mp.expected_home_goals)
    away = scorer_model.scorers(fx["away_team"], mp.expected_away_goals)
    return home + away


def _predict_rows(model: MatchModel, fixtures: pd.DataFrame, data_cutoff: pd.Timestamp,
                  version: str, scorer_model=None) -> list[dict]:
    if len(fixtures) == 0:
        return []
    probs = model.predict_proba(fixtures)
    mats = model.predict_score_matrix(fixtures)
    created = datetime.now(UTC).isoformat()
    rows = []
    for k in range(len(fixtures)):
        fx = fixtures.iloc[k]
        mp = market_probabilities(mats[k])
        played = fx["status"] == "played"
        pid = hashlib.sha1(f"{fx['match_id']}|{version}".encode()).hexdigest()[:16]
        rows.append({
            "prediction_id": pid,
            "match_id": fx["match_id"],
            "model_version_id": version,
            "data_cutoff": data_cutoff.strftime("%Y-%m-%d"),
            "created_at": created,
            "date": fx["date"].strftime("%Y-%m-%d"),
            "home_team": fx["home_team"], "away_team": fx["away_team"],
            "home_win_probability": round(float(probs[k, 0]), 4),
            "draw_probability": round(float(probs[k, 1]), 4),
            "away_win_probability": round(float(probs[k, 2]), 4),
            "expected_home_goals": round(mp.expected_home_goals, 3),
            "expected_away_goals": round(mp.expected_away_goals, 3),
            "expected_total_goals": round(mp.expected_total_goals, 3),
            "most_likely_score": mp.most_likely_score,
            "over_2_5": round(mp.over_2_5, 4), "btts_yes": round(mp.btts_yes, 4),
            "btts_no": round(mp.btts_no, 4),
            "over_under": mp.over_under,
            "total_goals_dist": mp.total_goals_dist,
            "home_clean_sheet": round(mp.home_clean_sheet, 4),
            "away_clean_sheet": round(mp.away_clean_sheet, 4),
            "home_win_to_nil": round(mp.home_win_to_nil, 4),
            "away_win_to_nil": round(mp.away_win_to_nil, 4),
            "top_scorelines": [{"score": s, "prob": round(p, 4)} for s, p in mp.top_scorelines],
            "scorers": _scorer_rows(scorer_model, fx, mp),
            "factors": _explain(model, fx, (mp.expected_home_goals, mp.expected_away_goals)),
            "is_frozen": True,
            "status": fx["status"],
            "home_score": None if not played else int(fx["home_score"]),
            "away_score": None if not played else int(fx["away_score"]),
        })
    return rows


def freeze_world_cup(matches: pd.DataFrame, tournament: Tournament,
                     model_factory: ModelFactory | None = None,
                     verbose: bool = True) -> dict:
    """Generate/refresh frozen predictions for all 72 group-stage matches."""
    STORE.mkdir(parents=True, exist_ok=True)
    model_factory = model_factory or (lambda: ProductionModel())
    played_all = matches[matches["status"] == "played"]

    existing_path = STORE / "predictions.jsonl"
    existing: dict[tuple[str, str], dict] = {}
    if existing_path.exists():
        for line in existing_path.read_text().splitlines():
            r = json.loads(line)
            existing[(r["match_id"], r["model_version_id"])] = r

    # Predict the whole tournament: group stage *and* the live knockout ties
    # (the latter live in a separate frame since they're cross-group fixtures).
    fixtures = tournament.fixtures
    if len(getattr(tournament, "knockout_fixtures", [])):
        fixtures = pd.concat(
            [tournament.fixtures, tournament.knockout_fixtures], ignore_index=True
        )
    new_rows: list[dict] = []

    # --- played matches: per-matchday pre-kickoff predictions (track record) ---
    played_wc = fixtures[fixtures["status"] == "played"]
    for d, day_matches in played_wc.groupby(played_wc["date"]):
        train = played_all[played_all["date"] < d]
        if len(train) < 1000:
            continue
        # cutoff = the true last date of data used (strictly before kickoff)
        cutoff = train["date"].max()
        model = model_factory().fit(train)
        version = model_version_id(model, cutoff)
        for r in _predict_rows(model, day_matches, cutoff, version):
            if (r["match_id"], r["model_version_id"]) not in existing:
                new_rows.append(r)
        if verbose:
            print(f"[freeze] matchday {pd.Timestamp(d).date()} -> {len(day_matches)} frozen "
                  f"(version {version})")

    # --- pending matches: predicted as of the data cutoff (today) ---
    pending = fixtures[fixtures["status"] != "played"]
    if len(pending):
        model = model_factory().fit(played_all)
        cutoff = played_all["date"].max()
        version = model_version_id(model, cutoff)
        # anytime-goalscorer layer, fit strictly on goals up to the cutoff
        scorer_model = None
        try:
            from wc2026.models.scorers import GoalscorerModel, load_goalscorers
            scorer_model = GoalscorerModel().fit(load_goalscorers(), cutoff)
        except Exception as e:  # pragma: no cover - scorer layer is best-effort
            if verbose:
                print(f"[freeze] goalscorer layer skipped: {e}")
        for r in _predict_rows(model, pending, cutoff, version, scorer_model=scorer_model):
            if (r["match_id"], r["model_version_id"]) not in existing:
                new_rows.append(r)
        if verbose:
            print(f"[freeze] {len(pending)} pending matches frozen (cutoff {cutoff.date()}, "
                  f"version {version})")

    # merge & persist (append-only)
    for r in new_rows:
        existing[(r["match_id"], r["model_version_id"])] = r
    with existing_path.open("w") as fh:
        for r in existing.values():
            fh.write(json.dumps(r, default=str) + "\n")

    # current view = latest version per match
    latest: dict[str, dict] = {}
    for r in existing.values():
        cur = latest.get(r["match_id"])
        if cur is None or r["created_at"] >= cur["created_at"]:
            latest[r["match_id"]] = r
    (STORE / "current.json").write_text(json.dumps(list(latest.values()), indent=2, default=str))

    track = _track_record(list(latest.values()))
    (STORE / "track_record.json").write_text(json.dumps(track, indent=2, default=str))
    if verbose:
        print(f"[freeze] total stored predictions: {len(existing)}; "
              f"new: {len(new_rows)}; track-record matches: {track['n']}")
    return {"stored": len(existing), "new": len(new_rows), "track_record": track}


def _track_record(rows: list[dict]) -> dict:
    """Aggregate scores over already-played frozen predictions."""
    played = [r for r in rows if r["status"] == "played" and r["home_score"] is not None]
    if not played:
        return {"n": 0}
    probs = np.array([[r["home_win_probability"], r["draw_probability"],
                       r["away_win_probability"]] for r in played])
    probs = probs / probs.sum(axis=1, keepdims=True)
    y = np.array([result_index(r["home_score"], r["away_score"]) for r in played])
    from wc2026.evaluation.metrics import (
        brier_score,
        log_loss_multiclass,
        rps_score,
    )
    correct = int((probs.argmax(axis=1) == y).sum())
    return {
        "n": len(played),
        "log_loss": round(log_loss_multiclass(probs, y), 4),
        "brier": round(brier_score(probs, y), 4),
        "rps": round(rps_score(probs, y), 4),
        "accuracy": round(correct / len(played), 4),
        "correct": correct,
        "matches": [
            {"date": r["date"], "home": r["home_team"], "away": r["away_team"],
             "score": f"{r['home_score']}-{r['away_score']}",
             "p": [r["home_win_probability"], r["draw_probability"], r["away_win_probability"]],
             "predicted": ["H", "D", "A"][int(probs[i].argmax())],
             "actual": ["H", "D", "A"][int(y[i])]}
            for i, r in enumerate(played)
        ],
    }
