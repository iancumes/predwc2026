#!/usr/bin/env python
"""Load pipeline artifacts into the relational database (idempotent).

Run AFTER `alembic upgrade head`. Reads the processed matches, frozen
predictions, model metadata and latest simulation, and writes them into the
schema defined in wc2026.db.models. Safe to re-run: it clears and re-inserts.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import delete
from wc2026.config import PATHS
from wc2026.data.ingest import load_matches
from wc2026.db.models import (
    DataSnapshot,
    IngestionRun,
    Match,
    ModelVersion,
    Prediction,
    PredictionScoreline,
    SimulationTeamResult,
    Team,
    TournamentSimulation,
)
from wc2026.db.session import session_factory
from wc2026.teams import confederation, team_code


def _read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def seed() -> None:
    Session = session_factory()
    matches = load_matches()
    preds = _read_json(PATHS.artifacts / "predictions" / "current.json", [])
    sim = _read_json(PATHS.simulations / "latest.json", {})
    meta = _read_json(PATHS.models / "production_meta.json", {})
    ingest_report = _read_json(PATHS.data_processed / "ingestion_report.json", {})

    with Session() as s:
        # clear in dependency order
        for model in (SimulationTeamResult, TournamentSimulation, PredictionScoreline,
                      Prediction, ModelVersion, Match, Team, DataSnapshot, IngestionRun):
            s.execute(delete(model))
        s.commit()

        # teams (union of all teams seen)
        names = pd.unique(pd.concat([matches["home_team"], matches["away_team"]]))
        s.add_all([Team(code=team_code(n), name=n, confederation=confederation(n)) for n in names])
        s.commit()

        # matches (bulk)
        s.bulk_save_objects([
            Match(
                match_id=r.match_id, date=r.date.date(),
                home_code=team_code(r.home_team), away_code=team_code(r.away_team),
                home_team=r.home_team, away_team=r.away_team,
                home_score=None if pd.isna(r.home_score) else int(r.home_score),
                away_score=None if pd.isna(r.away_score) else int(r.away_score),
                tournament=r.tournament, neutral_venue=bool(r.neutral_venue),
                is_world_cup=bool(r.is_world_cup), status=r.status,
                city=r.city, country=r.country, source=r.source,
            )
            for r in matches.itertuples(index=False)
        ])
        s.commit()

        # model versions (from predictions + production meta)
        versions = {p["model_version_id"]: p["data_cutoff"] for p in preds}
        for vid, cutoff in versions.items():
            s.add(ModelVersion(id=vid, name=meta.get("name", "production_ensemble"),
                               data_cutoff=pd.Timestamp(cutoff).date(),
                               calibration=meta.get("calibration"),
                               weights_json=json.dumps(meta.get("weights")),
                               metrics_json=None))
        s.commit()

        # predictions + scorelines
        for p in preds:
            s.add(Prediction(
                prediction_id=p["prediction_id"], match_id=p["match_id"],
                model_version_id=p["model_version_id"],
                data_cutoff=pd.Timestamp(p["data_cutoff"]).date(),
                created_at=datetime.fromisoformat(p["created_at"]),
                home_win_probability=p["home_win_probability"],
                draw_probability=p["draw_probability"],
                away_win_probability=p["away_win_probability"],
                expected_home_goals=p["expected_home_goals"],
                expected_away_goals=p["expected_away_goals"],
                is_frozen=p["is_frozen"],
            ))
            for sc in p.get("top_scorelines", []):
                h, a = sc["score"].split("-")
                s.add(PredictionScoreline(prediction_id=p["prediction_id"],
                                          home_goals=int(h), away_goals=int(a),
                                          probability=sc["prob"]))
        s.commit()

        # simulation
        if sim.get("teams"):
            ts = TournamentSimulation(n_sims=sim["n_sims"], seed=sim["seed"],
                                      model_version_id=None)
            s.add(ts)
            s.flush()
            for t in sim["teams"]:
                s.add(SimulationTeamResult(
                    simulation_id=ts.id, team_code=team_code(t["team"]),
                    p_win_group=t["p_win_group"], p_runner_up=t["p_runner_up"],
                    p_qualify_third=t["p_qualify_third"], p_reach_r32=t["p_reach_r32"],
                    p_reach_r16=t["p_reach_r16"], p_reach_qf=t["p_reach_qf"],
                    p_reach_sf=t["p_reach_sf"], p_reach_final=t["p_reach_final"],
                    p_champion=t["p_champion"], se_champion=t.get("se_champion"),
                ))
            s.commit()

        # provenance
        s.add(DataSnapshot(n_matches=len(matches),
                           date_min=matches["date"].min().date(),
                           date_max=matches["date"].max().date(),
                           source=ingest_report.get("source")))
        s.add(IngestionRun(finished_at=datetime.utcnow(), source=ingest_report.get("source"),
                           rows_in=ingest_report.get("rows_in"),
                           rows_out=ingest_report.get("rows_out"), status="ok"))
        s.commit()

        n_pred = s.query(Prediction).count()
        n_match = s.query(Match).count()
        n_team = s.query(Team).count()
        print(f"[seed] teams={n_team} matches={n_match} predictions={n_pred} "
              f"sim_teams={len(sim.get('teams', []))}")


if __name__ == "__main__":
    seed()
