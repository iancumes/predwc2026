"""Leakage-free feature engineering.

Everything is computed in a single chronological pass: for each match we read a
team's accumulated history *before* recording the current result, so no feature
can ever depend on the match it describes or on anything later (`as_of` = the
match kickoff).  ``tests/test_leakage.py`` enforces this property.

``build_all`` returns one feature row per played match (for training/backtest);
``transform`` produces features for future fixtures from the state left after
the last ``build_all`` call (the real deployment path).
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import partial

import numpy as np
import pandas as pd

from wc2026.config import EloConfig
from wc2026.models.elo import EloRatings, _mov_multiplier
from wc2026.teams import confederation

FEATURE_COLUMNS = [
    "elo_home", "elo_away", "elo_diff", "abs_elo_diff",
    "elo_mom_home", "elo_mom_away",
    "form_ppg_home", "form_ppg_away", "form_ppg_diff",
    "win_rate_home", "win_rate_away", "win_rate_diff",
    "gf_home", "ga_home", "gf_away", "ga_away",
    "gd_home", "gd_away", "gd_diff",
    "exp_home", "exp_away",
    "h2h_gd", "h2h_n",
    "rest_days_home", "rest_days_away",
    "same_confederation",
    "neutral", "is_world_cup", "tournament_weight",
]

_CONF_IDX = {"UEFA": 1, "CONMEBOL": 2, "CONCACAF": 3, "CAF": 4, "AFC": 5, "OFC": 6}


@dataclass
class _TeamState:
    history: deque = field(default_factory=lambda: deque(maxlen=10))  # (points, gf, ga)
    elo_hist: deque = field(default_factory=lambda: deque(maxlen=6))  # past elo snapshots
    n_matches: int = 0
    last_date: pd.Timestamp | None = None


class FeatureBuilder:
    def __init__(self, elo_cfg: EloConfig | None = None, form_window: int = 10):
        self.elo = EloRatings(elo_cfg)
        self.form_window = form_window
        self.state: dict[str, _TeamState] = defaultdict(_TeamState)
        # recent head-to-head: key=frozenset(pair) -> deque[(home_team, home_gd)]
        # partial(deque, maxlen=5) (not a lambda) so the fitted model stays picklable
        self.h2h: dict[frozenset, deque] = defaultdict(partial(deque, maxlen=5))

    def _team_feats(self, team: str, date: pd.Timestamp) -> dict:
        st = self.state[team]
        if st.history:
            pts = np.array([h[0] for h in st.history], dtype=float)
            gf = np.array([h[1] for h in st.history], dtype=float)
            ga = np.array([h[2] for h in st.history], dtype=float)
            # exponential recency weights (most recent = highest)
            wts = np.power(0.85, np.arange(len(pts))[::-1])
            wsum = wts.sum()
            ppg = float((pts * wts).sum() / wsum)
            gf_a = float((gf * wts).sum() / wsum)
            ga_a = float((ga * wts).sum() / wsum)
            win_rate = float((pts == 3).mean())
        else:
            ppg, gf_a, ga_a, win_rate = 1.0, 1.0, 1.0, 0.33
        # elo momentum = current rating minus rating ~form_window matches ago
        elo_now = self.elo.get(team)
        elo_mom = elo_now - st.elo_hist[0] if st.elo_hist else 0.0
        rest = 30.0 if st.last_date is None else min((date - st.last_date).days, 365)
        return {
            "ppg": ppg, "gf": gf_a, "ga": ga_a, "win_rate": win_rate,
            "gd": gf_a - ga_a, "exp": float(np.log1p(st.n_matches)),
            "elo_mom": float(elo_mom), "rest": float(rest),
        }

    def _h2h(self, home: str, away: str) -> tuple[float, float]:
        dq = self.h2h.get(frozenset((home, away)))
        if not dq:
            return 0.0, 0.0
        vals = [gd if ht == home else -gd for ht, gd in dq]
        return float(np.mean(vals)), float(len(vals))

    def _row(self, home, away, neutral, is_wc, tw, date) -> dict:
        rh, ra = self.elo.get(home), self.elo.get(away)
        ha = 0.0 if neutral else self.elo.cfg.home_advantage
        diff = rh + ha - ra
        fh = self._team_feats(home, date)
        fa = self._team_feats(away, date)
        h2h_gd, h2h_n = self._h2h(home, away)
        same_conf = float(confederation(home) == confederation(away)
                          and confederation(home) != "UNK")
        return {
            "elo_home": rh, "elo_away": ra, "elo_diff": diff, "abs_elo_diff": abs(diff),
            "elo_mom_home": fh["elo_mom"], "elo_mom_away": fa["elo_mom"],
            "form_ppg_home": fh["ppg"], "form_ppg_away": fa["ppg"],
            "form_ppg_diff": fh["ppg"] - fa["ppg"],
            "win_rate_home": fh["win_rate"], "win_rate_away": fa["win_rate"],
            "win_rate_diff": fh["win_rate"] - fa["win_rate"],
            "gf_home": fh["gf"], "ga_home": fh["ga"], "gf_away": fa["gf"], "ga_away": fa["ga"],
            "gd_home": fh["gd"], "gd_away": fa["gd"], "gd_diff": fh["gd"] - fa["gd"],
            "exp_home": fh["exp"], "exp_away": fa["exp"],
            "h2h_gd": h2h_gd, "h2h_n": h2h_n,
            "rest_days_home": fh["rest"], "rest_days_away": fa["rest"],
            "same_confederation": same_conf,
            "neutral": float(neutral), "is_world_cup": float(is_wc), "tournament_weight": float(tw),
        }

    def _update(self, home, away, hs, as_, neutral, tw, date) -> None:
        # Elo update (mirror EloRatings.run for a single match)
        rh, ra = self.elo.get(home), self.elo.get(away)
        ha = 0.0 if neutral else self.elo.cfg.home_advantage
        we = self.elo.expected(rh, ra, ha)
        w_home = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        g = _mov_multiplier(hs - as_) if self.elo.cfg.mov_enabled else 1.0
        k = self.elo.cfg.k_factor * float(tw)
        delta = k * g * (w_home - we)
        # snapshot pre-update elo for momentum, then apply
        self.state[home].elo_hist.append(rh)
        self.state[away].elo_hist.append(ra)
        self.elo.ratings[home] = rh + delta
        self.elo.ratings[away] = ra - delta
        # form history
        ph = 3 if hs > as_ else (1 if hs == as_ else 0)
        pa = 3 if as_ > hs else (1 if hs == as_ else 0)
        self.state[home].history.append((ph, hs, as_))
        self.state[away].history.append((pa, as_, hs))
        self.state[home].last_date = date
        self.state[away].last_date = date
        self.state[home].n_matches += 1
        self.state[away].n_matches += 1
        # head-to-head (record AFTER feature read so current match is excluded)
        self.h2h[frozenset((home, away))].append((home, hs - as_))

    def build_all(self, matches: pd.DataFrame) -> pd.DataFrame:
        played = matches[matches["status"] == "played"].sort_values(["date", "match_id"])
        rows = []
        for _, m in played.iterrows():
            feats = self._row(m["home_team"], m["away_team"], bool(m["neutral_venue"]),
                              bool(m["is_world_cup"]), float(m["tournament_weight"]), m["date"])
            feats["match_id"] = m["match_id"]
            feats["home_score"] = m["home_score"]
            feats["away_score"] = m["away_score"]
            rows.append(feats)
            self._update(m["home_team"], m["away_team"], m["home_score"], m["away_score"],
                         bool(m["neutral_venue"]), float(m["tournament_weight"]), m["date"])
        return pd.DataFrame(rows)

    def transform(self, fixtures: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, r in fixtures.iterrows():
            date = r["date"] if "date" in r and pd.notna(r.get("date")) else pd.Timestamp("2026-06-18")
            tw = float(r.get("tournament_weight", 1.0))
            is_wc = bool(r.get("is_world_cup", True))
            rows.append(self._row(r["home_team"], r["away_team"], bool(r["neutral_venue"]),
                                  is_wc, tw, date))
        return pd.DataFrame(rows)[FEATURE_COLUMNS]
