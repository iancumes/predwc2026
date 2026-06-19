"""Elo ratings (World-Football style) and an Elo-based match model.

The rating engine processes matches strictly in chronological order, so the
rating used for any match reflects *only* earlier matches — leakage-free by
construction.  ``pre_match_ratings`` exposes that as a feature for every match.

EloModel turns the rating difference into expected goals (two small fitted
regressions), then into an independent-Poisson score matrix, so it produces
consistent 1X2 *and* exact-score probabilities.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson

from wc2026.config import EloConfig
from wc2026.models.base import MatchModel, probs_from_matrix


def _mov_multiplier(goal_diff: int) -> float:
    g = abs(int(goal_diff))
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    return (11.0 + g) / 8.0


class EloRatings:
    """Online Elo engine."""

    def __init__(self, cfg: EloConfig | None = None):
        self.cfg = cfg or EloConfig()
        self.ratings: dict[str, float] = {}

    def get(self, team: str) -> float:
        return self.ratings.get(team, self.cfg.base_rating)

    def expected(self, r_home: float, r_away: float, home_adv: float) -> float:
        return 1.0 / (1.0 + 10 ** (-(r_home + home_adv - r_away) / 400.0))

    def run(self, matches: pd.DataFrame) -> pd.DataFrame:
        """Process *played* matches in date order, updating ratings.

        Returns a frame aligned to the played rows with pre-match ratings.
        """
        played = matches[matches["status"] == "played"].sort_values(
            ["date", "match_id"]
        )
        pre_home = np.empty(len(played))
        pre_away = np.empty(len(played))
        cfg = self.cfg

        for k, (_, m) in enumerate(played.iterrows()):
            h, a = m["home_team"], m["away_team"]
            rh, ra = self.get(h), self.get(a)
            pre_home[k] = rh
            pre_away[k] = ra
            hm = 0.0 if m["neutral_venue"] else 1.0
            ha = cfg.home_advantage * hm
            we_home = self.expected(rh, ra, ha)

            hs, as_ = m["home_score"], m["away_score"]
            w_home = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
            g = _mov_multiplier(hs - as_) if cfg.mov_enabled else 1.0
            k_eff = cfg.k_factor * float(m.get("tournament_weight", 0.5))
            delta = k_eff * g * (w_home - we_home)
            self.ratings[h] = rh + delta
            self.ratings[a] = ra - delta

        out = played[["match_id", "date", "home_team", "away_team",
                      "home_score", "away_score", "neutral_venue"]].copy()
        out["elo_home_pre"] = pre_home
        out["elo_away_pre"] = pre_away
        return out.reset_index(drop=True)


class EloModel(MatchModel):
    name = "elo"

    def __init__(self, cfg: EloConfig | None = None, max_goals: int = 10):
        self.cfg = cfg or EloConfig()
        self.max_goals = max_goals
        self.engine = EloRatings(self.cfg)
        # fitted goal mapping coefficients
        self._sup_a = 0.0      # supremacy = a*elo_diff
        self._tot_b0 = 1.3     # base total goals (log space handled below)
        self._tot_b1 = 0.0     # |elo_diff| effect on total
        self._fitted = False

    def _eff_diff(self, fixtures: pd.DataFrame) -> np.ndarray:
        rh = fixtures["home_team"].map(self.engine.get).to_numpy(dtype=float)
        ra = fixtures["away_team"].map(self.engine.get).to_numpy(dtype=float)
        hm = np.where(fixtures["neutral_venue"].to_numpy(), 0.0, 1.0)
        return rh + self.cfg.home_advantage * hm - ra

    def fit(self, matches: pd.DataFrame) -> EloModel:
        pre = self.engine.run(matches)
        hm = np.where(pre["neutral_venue"].to_numpy(), 0.0, 1.0)
        diff = (pre["elo_home_pre"] - pre["elo_away_pre"]).to_numpy() \
            + self.cfg.home_advantage * hm
        sup = (pre["home_score"] - pre["away_score"]).to_numpy(dtype=float)
        tot = (pre["home_score"] + pre["away_score"]).to_numpy(dtype=float)

        # supremacy ~ a * diff  (no intercept: even Elo => even supremacy)
        denom = float((diff * diff).sum())
        self._sup_a = float((diff * sup).sum() / denom) if denom > 0 else 0.0
        # total goals ~ b0 + b1*|diff|   (mismatches score a touch more)
        absd = np.abs(diff)
        X = np.column_stack([np.ones_like(absd), absd])
        coef, *_ = np.linalg.lstsq(X, tot, rcond=None)
        self._tot_b0, self._tot_b1 = float(coef[0]), float(coef[1])
        self._fitted = True
        return self

    def _expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        diff = self._eff_diff(fixtures)
        sup = self._sup_a * diff
        tot = np.clip(self._tot_b0 + self._tot_b1 * np.abs(diff), 0.4, None)
        eh = np.clip((tot + sup) / 2.0, 0.05, None)
        ea = np.clip((tot - sup) / 2.0, 0.05, None)
        return np.column_stack([eh, ea])

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        eg = self._expected_goals(fixtures)
        ks = np.arange(self.max_goals + 1)
        mats = []
        for eh, ea in eg:
            m = np.outer(poisson.pmf(ks, eh), poisson.pmf(ks, ea))
            mats.append(m / m.sum())
        return mats

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self._expected_goals(fixtures)

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        return np.array([probs_from_matrix(m) for m in self.predict_score_matrix(fixtures)])

    def ratings_table(self) -> pd.DataFrame:
        df = pd.DataFrame(
            [{"team": t, "elo": r} for t, r in self.engine.ratings.items()]
        )
        return df.sort_values("elo", ascending=False).reset_index(drop=True)

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "home_advantage": self.cfg.home_advantage,
            "k_factor": self.cfg.k_factor,
            "mov_enabled": self.cfg.mov_enabled,
            "supremacy_per_elo": self._sup_a,
            "total_goals_base": self._tot_b0,
            "n_teams_rated": len(self.engine.ratings),
        }
