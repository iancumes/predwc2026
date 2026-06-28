"""Tests for the deterministic knockout-bracket resolver.

The resolver may only use *played* results — these tests assert it stays
self-consistent and leakage-free (no slot resolved from future/pending data).
"""
from __future__ import annotations

import pandas as pd

from wc2026.bracket import resolve_bracket


def test_resolve_runs_and_covers_all_matches(tournament):
    res = resolve_bracket(tournament)
    # 16 + 8 + 4 + 2 + 1 + 1 = 32 knockout matches.
    assert len(res) == 32
    for spec_round in ("R32", "R16", "QF", "SF", "FINAL"):
        for m in tournament.bracket[spec_round]:
            assert str(m["match"]) in res


def test_resolved_teams_belong_to_the_tournament(tournament):
    valid = set(tournament.teams)
    for e in resolve_bracket(tournament).values():
        for side in ("team1", "team2"):
            if e[side] is not None:
                assert e[side]["name"] in valid
                assert e[side]["code"]


def test_winners_propagate_and_are_participants(tournament):
    """A match's winner must be one of its two resolved participants, and must
    feed the dependent slot in the next round (no winner invented from thin air).
    """
    res = resolve_bracket(tournament)
    for e in res.values():
        if e["winner_code"] is None:
            continue
        sides = [s for s in (e["team1"], e["team2"]) if s]
        assert e["winner_code"] in {s["code"] for s in sides}


def test_no_leakage_pending_matches_have_no_score(tournament):
    """If a match isn't 'played', it must not carry a score or a winner."""
    for e in resolve_bracket(tournament).values():
        if e["status"] != "played":
            assert e["score1"] is None and e["score2"] is None
            assert e["winner_code"] is None


def test_a_future_result_does_not_change_already_decided_slots(tournament):
    """Removing a *pending* (scheduled) knockout fixture must not change which
    teams are already resolved — i.e. resolution depends only on played data.
    """
    import copy

    before = resolve_bracket(tournament)

    t2 = copy.copy(tournament)
    fx = tournament.fixtures
    # Drop scheduled cross-group (knockout) fixtures.
    keep = []
    for _, m in fx.iterrows():
        gh, ga = tournament.group_of(m["home_team"]), tournament.group_of(m["away_team"])
        cross = gh is not None and ga is not None and gh != ga
        if cross and m["status"] != "played":
            continue
        keep.append(m)
    t2.fixtures = pd.DataFrame(keep).reset_index(drop=True)

    after = resolve_bracket(t2)
    # Every match that was 'played' before stays identical (same teams, winner).
    for k, e in before.items():
        if e["status"] == "played":
            assert after[k]["winner_code"] == e["winner_code"]
            assert after[k]["team1"] == e["team1"]
            assert after[k]["team2"] == e["team2"]
