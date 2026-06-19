"""The critical anti-leakage property.

A match's features must depend only on earlier matches. We verify it directly:
removing every match *after* a given match must leave that match's feature row
byte-for-byte identical.
"""
import numpy as np

from wc2026.features import FEATURE_COLUMNS, FeatureBuilder


def test_features_do_not_depend_on_future(synthetic_matches):
    full = FeatureBuilder().build_all(synthetic_matches)
    # choose a match in the middle
    target_id = full.iloc[400]["match_id"]
    target_date = synthetic_matches.set_index("match_id").loc[target_id, "date"]

    truncated = synthetic_matches[synthetic_matches["date"] <= target_date]
    trunc = FeatureBuilder().build_all(truncated)

    a = full[full["match_id"] == target_id][FEATURE_COLUMNS].to_numpy()
    b = trunc[trunc["match_id"] == target_id][FEATURE_COLUMNS].to_numpy()
    assert np.allclose(a, b), "feature row changed when future matches were removed (leakage!)"


def test_adding_future_blowout_does_not_change_past(synthetic_matches):
    import pandas as pd
    full = FeatureBuilder().build_all(synthetic_matches)
    target_id = full.iloc[200]["match_id"]
    # append an extreme future match
    future = synthetic_matches.iloc[[0]].copy()
    future["match_id"] = "future"
    future["date"] = synthetic_matches["date"].max() + pd.Timedelta(days=5)
    future["home_score"] = 99
    augmented = pd.concat([synthetic_matches, future], ignore_index=True)
    aug = FeatureBuilder().build_all(augmented)

    a = full[full["match_id"] == target_id][FEATURE_COLUMNS].to_numpy()
    b = aug[aug["match_id"] == target_id][FEATURE_COLUMNS].to_numpy()
    assert np.allclose(a, b)
