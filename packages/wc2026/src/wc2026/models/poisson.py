"""Independent Poisson model with per-team attack/defence and home advantage.

log E[goals] = intercept + attack[scorer] - defence[conceder] + home·is_home

Fitted as a single Poisson GLM (two observations per match) with time-decay
sample weights.  L2 regularisation resolves the attack/defence translation
degeneracy and shrinks rarely-seen teams toward the average.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor

from wc2026.models.base import MatchModel, probs_from_matrix


class PoissonModel(MatchModel):
    name = "poisson"

    def __init__(
        self,
        half_life_days: float = 730.0,
        alpha: float = 1e-3,
        max_goals: int = 10,
        min_train_date: str = "1994-01-01",
    ):
        self.half_life_days = half_life_days
        self.alpha = alpha
        self.max_goals = max_goals
        self.min_train_date = pd.Timestamp(min_train_date)
        self.teams_: list[str] = []
        self.idx_: dict[str, int] = {}
        self.attack_: np.ndarray | None = None
        self.defence_: np.ndarray | None = None
        self.intercept_ = 0.0
        self.home_ = 0.0
        self.as_of_: pd.Timestamp | None = None

    def _weights(self, dates: pd.Series, as_of: pd.Timestamp) -> np.ndarray:
        age = (as_of - dates).dt.days.to_numpy(dtype=float)
        return np.power(0.5, np.clip(age, 0, None) / self.half_life_days)

    def fit(self, matches: pd.DataFrame, as_of: pd.Timestamp | None = None) -> PoissonModel:
        played = matches[matches["status"] == "played"].copy()
        played = played[played["date"] >= self.min_train_date]
        if as_of is None:
            as_of = played["date"].max()
        self.as_of_ = as_of

        teams = sorted(set(played["home_team"]) | set(played["away_team"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        self.teams_, self.idx_ = teams, idx

        w = self._weights(played["date"], as_of)
        hi = played["home_team"].map(idx).to_numpy()
        ai = played["away_team"].map(idx).to_numpy()
        hm = np.where(played["neutral_venue"].to_numpy(), 0.0, 1.0)
        hs = played["home_score"].to_numpy(dtype=float)
        as_ = played["away_score"].to_numpy(dtype=float)
        m = len(played)

        # Two observations per match. Columns: [att(n) | def(n) | home(1)].
        rows = np.repeat(np.arange(2 * m), 3)
        # home-scoring obs r=2k, away-scoring obs r=2k+1
        att_col_home = hi
        def_col_home = n + ai
        att_col_away = ai
        def_col_away = n + hi
        cols = np.empty(2 * m * 3, dtype=int)
        data = np.empty(2 * m * 3, dtype=float)
        home_col = 2 * n
        # home obs
        cols[0::6] = att_col_home; data[0::6] = 1.0
        cols[1::6] = def_col_home; data[1::6] = -1.0
        cols[2::6] = home_col;     data[2::6] = hm
        # away obs
        cols[3::6] = att_col_away; data[3::6] = 1.0
        cols[4::6] = def_col_away; data[4::6] = -1.0
        cols[5::6] = home_col;     data[5::6] = 0.0

        X = sparse.csr_matrix((data, (rows, cols)), shape=(2 * m, 2 * n + 1))
        y = np.empty(2 * m); y[0::2] = hs; y[1::2] = as_
        sw = np.empty(2 * m); sw[0::2] = w; sw[1::2] = w

        glm = PoissonRegressor(alpha=self.alpha, fit_intercept=True, max_iter=300)
        glm.fit(X, y, sample_weight=sw)

        self.attack_ = glm.coef_[:n]
        self.defence_ = glm.coef_[n:2 * n]
        self.home_ = float(glm.coef_[2 * n])
        self.intercept_ = float(glm.intercept_)
        return self

    def _lambdas(self, fixtures: pd.DataFrame) -> np.ndarray:
        def att(t):
            i = self.idx_.get(t)
            return self.attack_[i] if i is not None else 0.0

        def dfc(t):
            i = self.idx_.get(t)
            return self.defence_[i] if i is not None else 0.0

        eh, ea = [], []
        for _, r in fixtures.iterrows():
            hm = 0.0 if r["neutral_venue"] else 1.0
            lh = np.exp(self.intercept_ + att(r["home_team"]) - dfc(r["away_team"]) + self.home_ * hm)
            la = np.exp(self.intercept_ + att(r["away_team"]) - dfc(r["home_team"]))
            eh.append(lh); ea.append(la)
        return np.column_stack([eh, ea])

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        lam = self._lambdas(fixtures)
        ks = np.arange(self.max_goals + 1)
        out = []
        for lh, la in lam:
            m = np.outer(poisson.pmf(ks, lh), poisson.pmf(ks, la))
            out.append(m / m.sum())
        return out

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self._lambdas(fixtures)

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        return np.array([probs_from_matrix(m) for m in self.predict_score_matrix(fixtures)])

    def metadata(self) -> dict:
        return {
            "name": self.name, "half_life_days": self.half_life_days,
            "alpha": self.alpha, "home_advantage_log": self.home_,
            "intercept": self.intercept_, "n_teams": len(self.teams_),
            "as_of": None if self.as_of_ is None else self.as_of_.strftime("%Y-%m-%d"),
        }
