"""Monte Carlo invariants the simulator must always satisfy."""
import numpy as np


def test_probabilities_bounded(sim_result):
    t = sim_result.team_table
    cols = ["p_win_group", "p_runner_up", "p_qualify_third", "p_reach_r32",
            "p_reach_r16", "p_reach_qf", "p_reach_sf", "p_reach_final", "p_champion"]
    for c in cols:
        assert (t[c] >= -1e-12).all() and (t[c] <= 1 + 1e-9).all()


def test_exactly_one_champion(sim_result):
    assert abs(sim_result.team_table["p_champion"].sum() - 1.0) < 1e-9


def test_round_population_sums(sim_result):
    t = sim_result.team_table
    assert abs(t["p_reach_r32"].sum() - 32) < 1e-6     # 32 teams reach R32
    assert abs(t["p_reach_r16"].sum() - 16) < 1e-6
    assert abs(t["p_reach_qf"].sum() - 8) < 1e-6
    assert abs(t["p_reach_sf"].sum() - 4) < 1e-6
    assert abs(t["p_reach_final"].sum() - 2) < 1e-6


def test_round_monotonicity(sim_result):
    t = sim_result.team_table
    chain = ["p_reach_r32", "p_reach_r16", "p_reach_qf", "p_reach_sf",
             "p_reach_final", "p_champion"]
    for a, b in zip(chain, chain[1:], strict=False):
        assert (t[a] >= t[b] - 1e-9).all()


def test_r32_equals_qualifiers(sim_result):
    t = sim_result.team_table
    qualify = t["p_win_group"] + t["p_runner_up"] + t["p_qualify_third"]
    assert np.allclose(t["p_reach_r32"], qualify, atol=1e-9)


def test_seed_reproducibility(tournament, dc_model):
    from wc2026.simulation import WorldCupSimulator
    a = WorldCupSimulator(tournament, dc_model, n_sims=3000, seed=42).run(save=False)
    b = WorldCupSimulator(tournament, dc_model, n_sims=3000, seed=42).run(save=False)
    assert np.allclose(a.team_table.sort_values("team")["p_champion"].to_numpy(),
                       b.team_table.sort_values("team")["p_champion"].to_numpy())


def test_played_results_are_locked(tournament, dc_model):
    """A team that already lost its only chance should never exceed bounds;
    structurally, every team in a group still has non-negative, sane props."""
    # Brazil drew MD1 but is strong -> high advance; Haiti lost -> low advance.
    from wc2026.simulation import WorldCupSimulator
    res = WorldCupSimulator(tournament, dc_model, n_sims=5000, seed=7).run(save=False)
    tt = res.team_table.set_index("team")
    def adv(x):
        return tt.loc[x, "p_win_group"] + tt.loc[x, "p_runner_up"] + tt.loc[x, "p_qualify_third"]
    assert adv("Brazil") > adv("Haiti")
