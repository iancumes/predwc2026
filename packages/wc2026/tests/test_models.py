import numpy as np
import pandas as pd
import pytest

from wc2026.models import DixonColesModel, EloModel, PoissonModel
from wc2026.models.base import market_probabilities, probs_from_matrix

FX = pd.DataFrame([
    {"home_team": "E", "away_team": "A", "neutral_venue": False,
     "is_world_cup": False, "tournament_weight": 0.3, "date": pd.Timestamp("2020-06-01")},
])


@pytest.mark.parametrize("Model", [EloModel, PoissonModel, DixonColesModel])
def test_probs_valid_simplex(Model, synthetic_matches):
    m = Model().fit(synthetic_matches)
    p = m.predict_proba(FX)
    assert p.shape == (1, 3)
    assert np.all(p >= 0)
    assert abs(p.sum() - 1.0) < 1e-6


@pytest.mark.parametrize("Model", [EloModel, PoissonModel, DixonColesModel])
def test_score_matrix_normalised(Model, synthetic_matches):
    m = Model().fit(synthetic_matches)
    mat = m.predict_score_matrix(FX)[0]
    assert mat.shape[0] == mat.shape[1]
    assert abs(mat.sum() - 1.0) < 1e-6
    # 1X2 derived from the matrix matches predict_proba
    assert np.allclose(probs_from_matrix(mat), m.predict_proba(FX)[0], atol=1e-6)


def test_stronger_team_favoured(synthetic_matches):
    # team F is strongest, A weakest in the synthetic fixture
    m = DixonColesModel().fit(synthetic_matches)
    fx = pd.DataFrame([{"home_team": "F", "away_team": "A", "neutral_venue": True,
                        "is_world_cup": False, "tournament_weight": 0.3,
                        "date": pd.Timestamp("2020-06-01")}])
    p = m.predict_proba(fx)[0]
    assert p[0] > p[2]  # home(F) win prob > away(A) win prob


def test_market_probabilities_consistency(synthetic_matches):
    m = PoissonModel().fit(synthetic_matches)
    mat = m.predict_score_matrix(FX)[0]
    mp = market_probabilities(mat)
    assert abs(mp.home_win + mp.draw + mp.away_win - 1.0) < 1e-6
    assert abs(mp.over_2_5 + mp.under_2_5 - 1.0) < 1e-6
    assert abs(mp.btts_yes + mp.btts_no - 1.0) < 1e-6
    assert 0 <= mp.expected_home_goals < 10


def test_dixon_coles_reproducible(synthetic_matches):
    a = DixonColesModel().fit(synthetic_matches).predict_proba(FX)
    b = DixonColesModel().fit(synthetic_matches).predict_proba(FX)
    assert np.allclose(a, b)
