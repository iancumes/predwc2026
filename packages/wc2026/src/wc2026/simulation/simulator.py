"""Vectorised Monte Carlo simulator for the FIFA World Cup 2026.

Design (all sims run in parallel as numpy arrays):

1. **Group stage** — played matches are locked from the live feed; pending
   matches are sampled scoreline-by-scoreline from the model's score matrix so
   goal-difference / goals-for tiebreakers are honoured.  Standings use the
   official FIFA order (points, GD, GF) with drawing-of-lots for residual ties.
2. **Best thirds** — the 8 best third-placed teams are ranked across groups and
   slotted into the bracket using FIFA's allowed-group constraints; the slot↔
   group mapping for every one of the C(12,8)=495 group combinations is solved
   once (constraint-respecting assignment) and looked up by bitmask per sim.
3. **Knockouts** — every tie is resolved with a precomputed neutral-venue
   "advance probability" matrix P[i,j] = P(i eliminates j), which folds extra
   time and penalties into a single Bernoulli draw, fully vectorised round by
   round up to the final.

Outputs per-team probabilities (win group, runner-up, qualify as best third,
reach each round, win the cup) with Monte Carlo standard errors.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from wc2026.config import PATHS
from wc2026.data.tournament import Tournament
from wc2026.models.base import MatchModel

ROUNDS = ["reach_r32", "reach_r16", "reach_qf", "reach_sf", "reach_final", "champion"]


@dataclass
class SimulationResult:
    n_sims: int
    seed: int
    model_name: str
    team_table: pd.DataFrame              # per-team probabilities + SE
    generated_at: str = ""
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "n_sims": self.n_sims, "seed": self.seed, "model": self.model_name,
            "generated_at": self.generated_at, "meta": self.meta,
            "teams": self.team_table.to_dict(orient="records"),
        }


class WorldCupSimulator:
    def __init__(self, tournament: Tournament, model: MatchModel,
                 n_sims: int = 50000, seed: int = 20260611, max_goals: int = 8):
        self.t = tournament
        self.model = model
        self.n_sims = int(n_sims)
        self.seed = int(seed)
        self.max_goals = max_goals
        self.id2team = tournament.teams                       # 48 names
        self.team2id = {t: i for i, t in enumerate(self.id2team)}
        self.group_letters = sorted(tournament.groups)        # A..L
        self.gl2idx = {g: i for i, g in enumerate(self.group_letters)}

    # ---- precompute knockout advance-probability matrix -------------------
    def _advance_matrix(self) -> np.ndarray:
        n = len(self.id2team)
        rows = []
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        for i, j in pairs:
            rows.append({
                "home_team": self.id2team[i], "away_team": self.id2team[j],
                "neutral_venue": True, "is_world_cup": True,
                "tournament_weight": 1.0, "date": pd.Timestamp("2026-07-01"),
            })
        probs = self.model.predict_proba(pd.DataFrame(rows))
        P = np.full((n, n), 0.5)
        for k, (i, j) in enumerate(pairs):
            ph, pdr, pa = probs[k]
            denom = ph + pa
            share = ph / denom if denom > 1e-9 else 0.5
            adv = ph + pdr * share                # i advances over j
            P[i, j] = adv
            P[j, i] = 1.0 - adv
        return P

    # ---- third-place assignment table (495 combinations) ------------------
    def _third_assignment_table(self) -> np.ndarray:
        """bitmask(12 bits) -> array(8) of group-idx assigned to each third slot.

        Slots are taken in R32 match order. Returns -1 rows for invalid masks.
        """
        slots = self.t.third_place_slots               # 8 dicts with 'allowed'
        allowed = [[self.gl2idx[g] for g in s["allowed"]] for s in slots]
        table = np.full((1 << 12, 8), -1, dtype=np.int8)
        from itertools import combinations
        for combo in combinations(range(12), 8):
            cost = np.full((8, 8), 1e6)               # rows=slots, cols=position in combo
            for si in range(8):
                for ci, g in enumerate(combo):
                    if g in allowed[si]:
                        cost[si, ci] = ci * 1e-3      # deterministic tiebreak
            r, c = linear_sum_assignment(cost)
            if cost[r, c].sum() >= 1e5:               # infeasible (shouldn't happen)
                continue
            mask = 0
            for g in combo:
                mask |= (1 << g)
            assign = np.empty(8, dtype=np.int8)
            for si, ci in zip(r, c, strict=True):
                assign[si] = combo[ci]
            table[mask] = assign
        return table

    # ---- group-stage goal sampling ----------------------------------------
    def _group_arrays(self, rng):
        """Per group: locked + sampled goals -> winners/runners/thirds ids + keys."""
        N = self.n_sims
        winners = np.empty((N, 12), dtype=np.int16)
        runners = np.empty((N, 12), dtype=np.int16)
        thirds = np.empty((N, 12), dtype=np.int16)
        thirds_key = np.empty((N, 12), dtype=np.float64)

        # pre-sample all pending fixtures from model score matrices
        pending = self.t.pending
        if len(pending):
            mats = self.model.predict_score_matrix(pending)
        sampled: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for k, (_, row) in enumerate(pending.iterrows()):
            m = mats[k]
            pmf = (m / m.sum()).ravel()
            g = m.shape[0]
            idx = rng.choice(g * g, size=N, p=pmf)
            sampled[row["match_id"]] = (idx // g, idx % g)   # (home_goals, away_goals)

        for gl in self.group_letters:
            gi = self.gl2idx[gl]
            teams = self.t.groups[gl]
            local = {t: k for k, t in enumerate(teams)}
            pts = np.zeros((N, 4)); gf = np.zeros((N, 4)); ga = np.zeros((N, 4))
            for _, mrow in self.t.group_fixtures(gl).iterrows():
                h = local[mrow["home_team"]]; a = local[mrow["away_team"]]
                if mrow["status"] == "played":
                    hg = np.full(N, int(mrow["home_score"]))
                    ag = np.full(N, int(mrow["away_score"]))
                else:
                    hg, ag = sampled[mrow["match_id"]]
                hw = hg > ag; dr = hg == ag; aw = ag > hg
                pts[:, h] += np.where(hw, 3, np.where(dr, 1, 0))
                pts[:, a] += np.where(aw, 3, np.where(dr, 1, 0))
                gf[:, h] += hg; ga[:, h] += ag; gf[:, a] += ag; ga[:, a] += hg
            gd = gf - ga
            key = pts * 1e6 + gd * 1e3 + gf + rng.random((N, 4)) * 1e-3
            order = np.argsort(-key, axis=1)
            gids = np.array([self.team2id[t] for t in teams])
            winners[:, gi] = gids[order[:, 0]]
            runners[:, gi] = gids[order[:, 1]]
            thirds[:, gi] = gids[order[:, 2]]
            # cross-group third ranking key: points, GD, GF
            third_pts = np.take_along_axis(pts, order[:, 2:3], axis=1)[:, 0]
            third_gd = np.take_along_axis(gd, order[:, 2:3], axis=1)[:, 0]
            third_gf = np.take_along_axis(gf, order[:, 2:3], axis=1)[:, 0]
            thirds_key[:, gi] = third_pts * 1e6 + third_gd * 1e3 + third_gf
        return winners, runners, thirds, thirds_key

    # ---- main run ---------------------------------------------------------
    def run(self, save: bool = True) -> SimulationResult:
        rng = np.random.default_rng(self.seed)
        N = self.n_sims
        n_teams = len(self.id2team)
        P = self._advance_matrix()
        third_table = self._third_assignment_table()

        winners, runners, thirds, thirds_key = self._group_arrays(rng)

        # best-8 thirds: rank 12 thirds per sim, pick top 8 groups
        jitter = rng.random((N, 12)) * 1e-6
        tkey = thirds_key + jitter
        order_thirds = np.argsort(-tkey, axis=1)           # group indices sorted
        top8_groups = order_thirds[:, :8]                  # (N,8) winning group idx
        bitmask = np.zeros(N, dtype=np.int32)
        for s in range(8):
            bitmask |= (1 << top8_groups[:, s].astype(np.int32))
        slot_group = third_table[bitmask]                  # (N,8) group idx per slot
        rowidx = np.arange(N)
        third_in_slot = np.empty((N, 8), dtype=np.int16)
        for s in range(8):
            third_in_slot[:, s] = thirds[rowidx, slot_group[:, s]]

        # ---- counters ----
        cnt = {r: np.zeros(n_teams) for r in ROUNDS}
        grp_first = np.zeros(n_teams); grp_second = np.zeros(n_teams)
        third_qual = np.zeros(n_teams); runner_up_final = np.zeros(n_teams)

        np.add.at(grp_first, winners.ravel(), 1)
        np.add.at(grp_second, runners.ravel(), 1)
        np.add.at(third_qual, third_in_slot.ravel(), 1)

        # ---- build R32 slots from bracket ----
        def resolve(tok: str, third_iter):
            kind = tok[0]
            if kind == "1":
                return winners[:, self.gl2idx[tok[1]]]
            if kind == "2":
                return runners[:, self.gl2idx[tok[1]]]
            # third slot: consume next third_in_slot column (R32 order)
            s = next(third_iter)
            return third_in_slot[:, s]

        third_counter = iter(range(8))
        match_winner: dict[int, np.ndarray] = {}
        r32_participants = []
        for spec in self.t.bracket["R32"]:
            a = resolve(spec["slot1"], third_counter)
            b = resolve(spec["slot2"], third_counter)
            r32_participants.extend([a, b])
            p = P[a, b]
            match_winner[spec["match"]] = np.where(rng.random(N) < p, a, b)
        for arr in r32_participants:
            np.add.at(cnt["reach_r32"], arr, 1)

        def play_round(specs):
            parts = []
            for spec in specs:
                a = match_winner[int(spec["slot1"][1:])]
                b = match_winner[int(spec["slot2"][1:])]
                parts.extend([a, b])
                p = P[a, b]
                match_winner[spec["match"]] = np.where(rng.random(N) < p, a, b)
            return parts

        for rnd_key, counter in [("R16", "reach_r16"), ("QF", "reach_qf"),
                                 ("SF", "reach_sf")]:
            parts = play_round(self.t.bracket[rnd_key])
            for arr in parts:
                np.add.at(cnt[counter], arr, 1)

        # final
        fspec = self.t.bracket["FINAL"][0]
        fa = match_winner[int(fspec["slot1"][1:])]
        fb = match_winner[int(fspec["slot2"][1:])]
        for arr in (fa, fb):
            np.add.at(cnt["reach_final"], arr, 1)
        champ = np.where(rng.random(N) < P[fa, fb], fa, fb)
        np.add.at(cnt["champion"], champ, 1)
        runner = np.where(champ == fa, fb, fa)
        np.add.at(runner_up_final, runner, 1)

        # ---- assemble table ----
        def prob(c):
            return c / N

        def se(p):
            return np.sqrt(np.clip(p * (1 - p), 0, None) / N)

        rows = []
        for tid, team in enumerate(self.id2team):
            p_champ = prob(cnt["champion"][tid])
            rows.append({
                "team": team, "code": team, "group": self.t.group_of(team),
                "confederation": None,
                "p_win_group": prob(grp_first[tid]),
                "p_runner_up": prob(grp_second[tid]),
                "p_qualify_third": prob(third_qual[tid]),
                "p_reach_r32": prob(cnt["reach_r32"][tid]),
                "p_reach_r16": prob(cnt["reach_r16"][tid]),
                "p_reach_qf": prob(cnt["reach_qf"][tid]),
                "p_reach_sf": prob(cnt["reach_sf"][tid]),
                "p_reach_final": prob(cnt["reach_final"][tid]),
                "p_champion": p_champ,
                "se_champion": se(p_champ),
            })
        from wc2026.teams import confederation, team_code
        table = pd.DataFrame(rows)
        table["code"] = table["team"].map(team_code)
        table["confederation"] = table["team"].map(confederation)
        table = table.sort_values("p_champion", ascending=False).reset_index(drop=True)

        # integrity: champion probs sum to ~1
        assert abs(table["p_champion"].sum() - 1.0) < 1e-6, "champion probs must sum to 1"

        from datetime import datetime
        result = SimulationResult(
            n_sims=N, seed=self.seed, model_name=self.model.name,
            team_table=table,
            generated_at=datetime.now(UTC).isoformat(),
            meta={"played_group_matches": int(len(self.t.played)),
                  "pending_group_matches": int(len(self.t.pending))},
        )
        if save:
            PATHS.simulations.mkdir(parents=True, exist_ok=True)
            (PATHS.simulations / "latest.json").write_text(
                json.dumps(result.to_json(), indent=2, default=str))
            table.to_parquet(PATHS.simulations / "latest_team_table.parquet", index=False)
        return result
