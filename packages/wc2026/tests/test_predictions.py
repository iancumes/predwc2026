"""Prediction freezing / auditability invariants."""
import json

import pandas as pd
import pytest

from wc2026.config import PATHS
from wc2026.predictions import model_version_id

STORE = PATHS.artifacts / "predictions" / "predictions.jsonl"


def test_version_id_deterministic():
    class Dummy:
        name = "dummy"

        def metadata(self):
            return {"a": 1, "b": 2}

    cut = pd.Timestamp("2026-06-01")
    assert model_version_id(Dummy(), cut) == model_version_id(Dummy(), cut)


def test_frozen_predictions_are_pre_kickoff():
    """For played matches, the data cutoff must be strictly before the match
    date — i.e. the prediction could not have seen the result."""
    if not STORE.exists():
        pytest.skip("run `wc2026 freeze` first")
    rows = [json.loads(ln) for ln in STORE.read_text().splitlines()]
    played = [r for r in rows if r["status"] == "played"]
    assert played, "expected some frozen predictions for played matches"
    for r in played:
        assert r["is_frozen"] is True
        assert pd.Timestamp(r["data_cutoff"]) < pd.Timestamp(r["date"]), (
            f"prediction for {r['home_team']} v {r['away_team']} used data on/after kickoff"
        )


def test_prediction_store_keys_unique():
    if not STORE.exists():
        pytest.skip("run `wc2026 freeze` first")
    rows = [json.loads(ln) for ln in STORE.read_text().splitlines()]
    keys = [(r["match_id"], r["model_version_id"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate (match_id, version) — store not append-only"
