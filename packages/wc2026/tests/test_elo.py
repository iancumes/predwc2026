
from wc2026.config import EloConfig
from wc2026.models.elo import EloRatings, _mov_multiplier


def test_expected_score_symmetry():
    e = EloRatings()
    assert abs(e.expected(1500, 1500, 0) - 0.5) < 1e-9
    # higher rating -> >0.5
    assert e.expected(1700, 1500, 0) > 0.5
    # expected scores of the two sides sum to 1
    assert abs(e.expected(1700, 1500, 0) + e.expected(1500, 1700, 0) - 1.0) < 1e-9


def test_elo_update_zero_sum_and_direction():
    e = EloRatings(EloConfig(k_factor=40, home_advantage=0, mov_enabled=False))
    import pandas as pd
    m = pd.DataFrame([{
        "match_id": "x", "date": pd.Timestamp("2020-01-01"), "home_team": "A",
        "away_team": "B", "home_score": 1, "away_score": 0, "neutral_venue": True,
        "status": "played", "tournament_weight": 1.0,
    }])
    e.run(m)
    # winner gains exactly what loser loses
    assert abs((e.get("A") - 1500) + (e.get("B") - 1500)) < 1e-9
    assert e.get("A") > 1500 > e.get("B")


def test_mov_multiplier_monotone():
    assert _mov_multiplier(0) == 1.0
    assert _mov_multiplier(1) == 1.0
    assert _mov_multiplier(2) == 1.5
    assert _mov_multiplier(5) > _mov_multiplier(3)


def test_ratings_reproducible(synthetic_matches):
    from wc2026.models.elo import EloModel
    a = EloModel().fit(synthetic_matches).engine.ratings
    b = EloModel().fit(synthetic_matches).engine.ratings
    assert a == b
