from itertools import combinations

import numpy as np


def test_structure_integrity(tournament):
    assert len(tournament.groups) == 12
    assert all(len(v) == 4 for v in tournament.groups.values())
    assert len(tournament.teams) == 48
    assert tournament.validate() == []  # official groups match live fixtures


def test_bracket_completeness(tournament):
    b = tournament.bracket
    assert len(b["R32"]) == 16
    assert len(b["R16"]) == 8
    assert len(b["QF"]) == 4
    assert len(b["SF"]) == 2
    assert len(b["FINAL"]) == 1
    # exactly 8 third-place slots
    assert len(tournament.third_place_slots) == 8


def test_third_place_assignment_feasible(tournament, dc_model):
    from wc2026.simulation import WorldCupSimulator
    sim = WorldCupSimulator(tournament, dc_model, n_sims=10, seed=1)
    table = sim._third_assignment_table()
    slots = tournament.third_place_slots
    allowed = [{sim.gl2idx[g] for g in s["allowed"]} for s in slots]
    # check several random 8-of-12 group combinations
    rng = np.random.default_rng(0)
    combos = list(combinations(range(12), 8))
    for combo in [combos[0], combos[-1]] + [combos[i] for i in rng.integers(0, len(combos), 20)]:
        mask = 0
        for g in combo:
            mask |= (1 << g)
        assign = table[mask]
        assert -1 not in assign, "no valid third-place assignment found"
        # each assigned group must be in the combo and respect the slot constraint
        assert set(assign.tolist()) == set(combo)
        for si, g in enumerate(assign):
            assert g in allowed[si]
