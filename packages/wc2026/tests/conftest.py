"""Shared pytest fixtures.

Uses the real ingested data when available (fast — models fit in <1s on a recent
window) and falls back to skipping data-dependent tests if the pipeline has not
been run yet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from wc2026.config import PATHS


@pytest.fixture(scope="session")
def matches():
    path = PATHS.data_processed / "matches.parquet"
    if not path.exists():
        pytest.skip("run `wc2026 ingest` first")
    from wc2026.data.ingest import load_matches
    return load_matches()


@pytest.fixture(scope="session")
def tournament():
    path = PATHS.data_processed / "matches.parquet"
    if not path.exists():
        pytest.skip("run `wc2026 ingest` first")
    from wc2026.data.tournament import load_tournament
    return load_tournament()


@pytest.fixture(scope="session")
def dc_model(matches):
    from wc2026.models.dixon_coles import DixonColesModel
    return DixonColesModel(min_train_date="2016-01-01").fit(matches)


@pytest.fixture(scope="session")
def sim_result(tournament, dc_model):
    from wc2026.simulation import WorldCupSimulator
    sim = WorldCupSimulator(tournament, dc_model, n_sims=8000, seed=123)
    return sim.run(save=False)


@pytest.fixture
def synthetic_matches():
    """Small deterministic match set for model unit tests."""
    rng = np.random.default_rng(0)
    teams = ["A", "B", "C", "D", "E", "F"]
    strength = {t: i * 0.2 for i, t in enumerate(teams)}
    rows = []
    start = pd.Timestamp("2015-01-01")
    for i in range(800):
        h, a = rng.choice(teams, size=2, replace=False)
        lh = np.exp(0.2 + strength[h] - strength[a] + 0.2)
        la = np.exp(0.2 + strength[a] - strength[h])
        rows.append({
            "match_id": f"m{i}", "date": start + pd.Timedelta(days=i * 3),
            "home_team": h, "away_team": a,
            "home_score": rng.poisson(lh), "away_score": rng.poisson(la),
            "tournament": "Friendly", "neutral_venue": False,
            "is_world_cup": False, "tournament_weight": 0.3,
            "status": "played", "confederation_home": "X", "confederation_away": "X",
        })
    return pd.DataFrame(rows)
