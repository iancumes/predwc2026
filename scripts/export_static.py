"""Export every API response as static JSON for a backend-free deployment.

The FastAPI service is a *thin read layer* over the pipeline artifacts, so we can
materialise every read endpoint as a static file and drop the running backend
entirely.  This script writes ``apps/web/public/data/**`` mirroring the API:

    health.json                      GET /health
    teams.json                       GET /api/teams
    teams/<code>.json                GET /api/teams/{code}
    matches.json                     GET /api/matches
    matches/<match_id>.json          GET /api/matches/{id}   (includes prediction)
    groups.json                      GET /api/groups
    probabilities.json               GET /api/tournament/probabilities
    bracket.json                     GET /api/tournament/bracket
    metrics.json                     GET /api/model/metrics
    calibration.json                 GET /api/model/calibration
    scorers.json                     anytime-goalscorer board (new)
    manifest.json                    freshness metadata for the UI

The Next.js app fetches these directly, so the whole site is static and free to
host (Vercel).  Re-run after every pipeline refresh (`make refresh`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The presentation logic lives in the API's store module (single source of
# truth); reuse it instead of duplicating the shaping here.  We add both the
# engine source and the API app to sys.path so this runs from a clean checkout
# without relying on an editable install being resolvable.
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "wc2026" / "src"))

from app import store  # noqa: E402

OUT = ROOT / "apps" / "web" / "public" / "data"


def _write(rel: str, obj: object) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    )


def export(verbose: bool = True) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)

    # --- meta / health -----------------------------------------------------
    status = store.status()
    _write("health.json", {"status": "ok", **status})

    # --- teams -------------------------------------------------------------
    teams = store.teams()
    _write("teams.json", {"teams": teams})
    for t in teams:
        detail = store.team_detail(t["code"])
        if detail is not None:
            _write(f"teams/{t['code']}.json", detail)

    # --- matches (+ per-match detail with frozen prediction) ---------------
    matches = store.matches()
    _write("matches.json", {"matches": matches})
    for m in matches:
        detail = store.match_detail(m["match_id"])
        if detail is not None:
            _write(f"matches/{m['match_id']}.json", detail)

    # --- groups ------------------------------------------------------------
    _write("groups.json", {"groups": store.groups()})

    # --- tournament --------------------------------------------------------
    sim = store.sim_results()
    _write("probabilities.json", {
        "n_sims": sim.get("n_sims"), "seed": sim.get("seed"),
        "model": sim.get("model"), "teams": sim.get("teams"),
    })
    _write("bracket.json", store.bracket())

    # --- model -------------------------------------------------------------
    s = store.backtest_summary()
    _write("metrics.json", {
        "overall": s.get("overall"), "ensemble_weights": s.get("ensemble_weights"),
        "calibration": s.get("calibration_method"), "n_test": s.get("n_test"),
        "slices": s.get("slices"), "track_record": store.track_record(),
        "model_meta": store.model_meta(),
    })
    _write("calibration.json", store.model_calibration())

    # --- goalscorers board (optional artifact) -----------------------------
    scorers = store.scorers_board() if hasattr(store, "scorers_board") else {}
    _write("scorers.json", scorers)

    # --- freshness manifest the UI can surface -----------------------------
    manifest = {
        "generated_at": sim.get("generated_at"),
        "data_cutoff": status.get("data_cutoff"),
        "model": status.get("model"),
        "n_sims": status.get("n_sims"),
        "n_matches": len(matches),
        "n_teams": len(teams),
        "played_group_matches": status.get("played_group_matches"),
        "pending_group_matches": status.get("pending_group_matches"),
    }
    _write("manifest.json", manifest)

    if verbose:
        print(f"[export] wrote {len(matches)} matches, {len(teams)} teams -> {OUT}")
    return manifest


if __name__ == "__main__":
    export()
