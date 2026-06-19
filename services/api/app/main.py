"""FastAPI application exposing predictions, standings, bracket and metrics.

Read endpoints are backed by pipeline artifacts (see store.py) and always
answer (degrading to demo_mode when artifacts are absent).  Admin endpoints
(ingest/train) are guarded by a configurable bearer token and run in the
background with a simple in-process idempotency lock.
"""
from __future__ import annotations

import os
import threading
import time

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import store

app = FastAPI(
    title="FIFA World Cup 2026 Predictor API",
    version="0.1.0",
    description="Analytical, informational match & tournament predictions. "
                "Probabilities are estimates, not guarantees.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("WC2026_CORS_ORIGINS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

ADMIN_TOKEN = os.environ.get("WC2026_ADMIN_TOKEN", "")
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _require_admin(authorization: str | None) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(503, "Admin endpoints disabled: set WC2026_ADMIN_TOKEN.")
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(401, "Invalid or missing admin token.")


# --------------------------------------------------------------------------- #
@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", **store.status()}


@app.get("/api/teams", tags=["teams"])
def get_teams() -> dict:
    return {"teams": store.teams()}


@app.get("/api/teams/{code}", tags=["teams"])
def get_team(code: str) -> dict:
    t = store.team_detail(code)
    if t is None:
        raise HTTPException(404, f"Unknown team code '{code}'.")
    return t


@app.get("/api/matches", tags=["matches"])
def get_matches(
    group: str | None = Query(None, description="Group letter A-L"),
    status: str | None = Query(None, description="played | scheduled"),
    team: str | None = Query(None, description="team code"),
) -> dict:
    return {"matches": store.matches(group=group, status_filter=status, team=team)}


@app.get("/api/matches/{match_id}", tags=["matches"])
def get_match(match_id: str) -> dict:
    m = store.match_detail(match_id)
    if m is None:
        raise HTTPException(404, "Match not found.")
    return m


@app.get("/api/matches/{match_id}/prediction", tags=["matches"])
def get_match_prediction(match_id: str) -> dict:
    m = store.match_detail(match_id)
    if m is None:
        raise HTTPException(404, "Match not found.")
    if not m.get("prediction"):
        raise HTTPException(404, "No frozen prediction for this match yet. Run `wc2026 freeze`.")
    return m["prediction"]


@app.get("/api/groups", tags=["groups"])
def get_groups() -> dict:
    return {"groups": store.groups()}


@app.get("/api/groups/{group_id}", tags=["groups"])
def get_group(group_id: str) -> dict:
    g = store.groups().get(group_id.upper())
    if g is None:
        raise HTTPException(404, f"Unknown group '{group_id}'.")
    return {"group": group_id.upper(), "standings": g}


@app.get("/api/tournament/probabilities", tags=["tournament"])
def tournament_probabilities() -> dict:
    sim = store.sim_results()
    if not sim:
        raise HTTPException(404, "No simulation yet. Run `wc2026 simulate`.")
    return {"n_sims": sim.get("n_sims"), "seed": sim.get("seed"),
            "model": sim.get("model"), "teams": sim.get("teams")}


@app.get("/api/tournament/bracket", tags=["tournament"])
def tournament_bracket() -> dict:
    return store.bracket()


@app.get("/api/model/metrics", tags=["model"])
def model_metrics() -> dict:
    s = store.backtest_summary()
    if not s:
        raise HTTPException(404, "No backtest yet. Run `wc2026 backtest`.")
    return {"overall": s.get("overall"), "ensemble_weights": s.get("ensemble_weights"),
            "calibration": s.get("calibration_method"), "n_test": s.get("n_test"),
            "slices": s.get("slices"), "track_record": store.track_record(),
            "model_meta": store.model_meta()}


@app.get("/api/model/calibration", tags=["model"])
def model_calibration() -> dict:
    return store.model_calibration()


class SimRequest(BaseModel):
    n_sims: int = Field(50000, ge=1000, le=200000)
    seed: int = Field(20260611)


@app.post("/api/simulations", tags=["tournament"])
def run_simulation(req: SimRequest) -> dict:
    import pickle

    from wc2026.config import PATHS
    from wc2026.data.tournament import load_tournament
    from wc2026.simulation import WorldCupSimulator
    model_path = PATHS.models / "production.pkl"
    if not model_path.exists():
        raise HTTPException(503, "No trained model. Run `wc2026 train` first.")
    with model_path.open("rb") as fh:
        model = pickle.load(fh)
    sim = WorldCupSimulator(load_tournament(), model, n_sims=req.n_sims, seed=req.seed)
    res = sim.run(save=False)
    return {"n_sims": res.n_sims, "seed": res.seed, "model": res.model_name,
            "teams": res.team_table.head(48).to_dict(orient="records")}


def _run_job(name: str, fn) -> None:
    with _LOCK:
        if _JOBS.get(name, {}).get("status") == "running":
            return
        _JOBS[name] = {"status": "running", "started": time.time()}
    try:
        fn()
        _JOBS[name] = {"status": "done", "finished": time.time()}
    except Exception as e:  # pragma: no cover
        _JOBS[name] = {"status": "error", "error": str(e)}


@app.post("/api/admin/ingest", status_code=202, tags=["admin"])
def admin_ingest(background: BackgroundTasks, authorization: str | None = Header(None)) -> dict:
    _require_admin(authorization)
    from wc2026.data.ingest import ingest
    if _JOBS.get("ingest", {}).get("status") == "running":
        return {"status": "already_running", "job": "ingest"}
    background.add_task(_run_job, "ingest", lambda: ingest(verbose=False))
    return {"status": "accepted", "job": "ingest"}


@app.post("/api/admin/train", status_code=202, tags=["admin"])
def admin_train(background: BackgroundTasks, authorization: str | None = Header(None)) -> dict:
    _require_admin(authorization)
    if _JOBS.get("train", {}).get("status") == "running":
        return {"status": "already_running", "job": "train"}

    def _train():
        import pickle

        from wc2026.config import PATHS
        from wc2026.data.ingest import load_matches
        from wc2026.models.production import ProductionModel
        m = load_matches()
        model = ProductionModel().fit(m)
        with (PATHS.models / "production.pkl").open("wb") as fh:
            pickle.dump(model, fh)

    background.add_task(_run_job, "train", _train)
    return {"status": "accepted", "job": "train"}


@app.get("/api/admin/jobs", tags=["admin"])
def admin_jobs(authorization: str | None = Header(None)) -> dict:
    _require_admin(authorization)
    return {"jobs": _JOBS}
