"""Dixon–Coles (1997) bivariate-Poisson model with time decay.

λ_home = exp(att[h] - def[a] + γ·home)     μ_away = exp(att[a] - def[h])

with the low-score dependence correction τ(x, y; λ, μ, ρ) and exponential
time-decay weights.  Fitted by penalised maximum likelihood (small ridge prior
on attack/defence) using L-BFGS-B with an **analytic gradient**, which keeps the
~2n+1 parameter optimisation fast enough to refit every walk-forward fold.

Identifiability: attack is constrained to sum to zero (last team = −Σ others).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from wc2026.config import DixonColesConfig
from wc2026.models.base import MatchModel, probs_from_matrix


def _tau_and_grad(x, y, lh, la, rho):
    """τ and its partials wrt λ_home(lh), λ_away(la), ρ — vectorised over matches."""
    tau = np.ones_like(lh)
    dl = np.zeros_like(lh)   # ∂τ/∂lh
    da = np.zeros_like(lh)   # ∂τ/∂la
    dr = np.zeros_like(lh)   # ∂τ/∂rho

    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)

    tau[m00] = 1.0 - lh[m00] * la[m00] * rho
    dl[m00] = -la[m00] * rho
    da[m00] = -lh[m00] * rho
    dr[m00] = -lh[m00] * la[m00]

    tau[m01] = 1.0 + lh[m01] * rho
    dl[m01] = rho
    dr[m01] = lh[m01]

    tau[m10] = 1.0 + la[m10] * rho
    da[m10] = rho
    dr[m10] = la[m10]

    tau[m11] = 1.0 - rho
    dr[m11] = -1.0

    return tau, dl, da, dr


class DixonColesModel(MatchModel):
    name = "dixon_coles"

    def __init__(
        self,
        cfg: DixonColesConfig | None = None,
        min_train_date: str = "1994-01-01",
        ridge: float = 1e-3,
        min_matches: int = 4,
    ):
        self.cfg = cfg or DixonColesConfig()
        self.min_train_date = pd.Timestamp(min_train_date)
        self.ridge = ridge
        self.min_matches = min_matches
        self.teams_: list[str] = []
        self.idx_: dict[str, int] = {}
        self.attack_: np.ndarray | None = None
        self.defence_: np.ndarray | None = None
        self.ha_ = self.cfg.ha_init
        self.rho_ = self.cfg.rho_init
        self.as_of_: pd.Timestamp | None = None
        self._params0: np.ndarray | None = None  # warm-start cache

    # -- training -----------------------------------------------------------
    def fit(
        self,
        matches: pd.DataFrame,
        as_of: pd.Timestamp | None = None,
        warm_start: np.ndarray | None = None,
    ) -> DixonColesModel:
        played = matches[matches["status"] == "played"].copy()
        played = played[played["date"] >= self.min_train_date]
        if as_of is not None:
            played = played[played["date"] < as_of]
        else:
            as_of = played["date"].max()
        self.as_of_ = as_of

        counts = pd.concat([played["home_team"], played["away_team"]]).value_counts()
        keep = set(counts[counts >= self.min_matches].index)
        played = played[played["home_team"].isin(keep) & played["away_team"].isin(keep)]

        teams = sorted(set(played["home_team"]) | set(played["away_team"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        self.teams_, self.idx_ = teams, idx

        hi = played["home_team"].map(idx).to_numpy()
        ai = played["away_team"].map(idx).to_numpy()
        hm = np.where(played["neutral_venue"].to_numpy(), 0.0, 1.0)
        x = played["home_score"].to_numpy(dtype=float)
        yv = played["away_score"].to_numpy(dtype=float)
        age = (as_of - played["date"]).dt.days.to_numpy(dtype=float)
        w = np.power(0.5, np.clip(age, 0, None) / self.cfg.half_life_days)

        n_att_free = n - 1
        ha_i, rho_i = n_att_free + n, n_att_free + n + 1
        ridge = self.ridge

        def unpack(theta):
            free = theta[:n_att_free]
            att = np.concatenate([free, [-free.sum()]])
            dfc = theta[n_att_free:n_att_free + n]
            return att, dfc, theta[ha_i], theta[rho_i]

        def nll_grad(theta):
            att, dfc, ha, rho = unpack(theta)
            log_lh = att[hi] - dfc[ai] + ha * hm
            log_la = att[ai] - dfc[hi]
            lh = np.exp(np.clip(log_lh, -6, 6))
            la = np.exp(np.clip(log_la, -6, 6))
            tau, dtl, dta, dtr = _tau_and_grad(x, yv, lh, la, rho)
            tau = np.clip(tau, 1e-8, None)

            ll = w * (np.log(tau) + x * log_lh - lh + yv * log_la - la)
            nll = -ll.sum() + ridge * (att @ att + dfc @ dfc)

            glh = (x - lh) + (dtl / tau) * lh          # ∂LL/∂log_lh per match
            gla = (yv - la) + (dta / tau) * la
            grho = (dtr / tau)

            g_att = np.zeros(n)
            g_def = np.zeros(n)
            np.add.at(g_att, hi, w * glh)
            np.add.at(g_att, ai, w * gla)
            np.add.at(g_def, ai, -w * glh)
            np.add.at(g_def, hi, -w * gla)
            g_ha = float((w * glh * hm).sum())
            g_rho = float((w * grho).sum())

            # negate (NLL) + ridge derivative
            g_att = -g_att + 2 * ridge * att
            g_def = -g_def + 2 * ridge * dfc
            g_ha = -g_ha
            g_rho = -g_rho
            # attack sum-to-zero reparam: ∂/∂free_i = g_att[i] - g_att[last]
            g_free = g_att[:-1] - g_att[-1]

            grad = np.concatenate([g_free, g_def, [g_ha, g_rho]])
            return nll, grad

        x0 = np.zeros(n_att_free + n + 2)
        x0[ha_i] = self.cfg.ha_init
        x0[rho_i] = self.cfg.rho_init
        if warm_start is not None and warm_start.shape == x0.shape:
            x0 = warm_start.copy()

        bounds = (
            [(-3, 3)] * n_att_free + [(-3, 3)] * n + [(-1.0, 1.0), (-0.2, 0.2)]
        )
        res = minimize(nll_grad, x0, jac=True, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": 200, "ftol": 1e-9})

        att, dfc, ha, rho = unpack(res.x)
        self.attack_, self.defence_ = att, dfc
        self.ha_, self.rho_ = float(ha), float(rho)
        self._params0 = res.x
        return self

    # -- prediction ---------------------------------------------------------
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
            eh.append(np.exp(att(r["home_team"]) - dfc(r["away_team"]) + self.ha_ * hm))
            ea.append(np.exp(att(r["away_team"]) - dfc(r["home_team"])))
        return np.column_stack([eh, ea])

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        lam = self._lambdas(fixtures)
        g = self.cfg.max_goals
        ks = np.arange(g + 1)
        rho = self.rho_
        mats = []
        for lh, la in lam:
            m = np.outer(poisson.pmf(ks, lh), poisson.pmf(ks, la))
            # Dixon–Coles low-score correction on the 2×2 corner
            m[0, 0] *= 1.0 - lh * la * rho
            m[0, 1] *= 1.0 + lh * rho
            m[1, 0] *= 1.0 + la * rho
            m[1, 1] *= 1.0 - rho
            m = np.clip(m, 0, None)
            mats.append(m / m.sum())
        return mats

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        return self._lambdas(fixtures)

    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        return np.array([probs_from_matrix(m) for m in self.predict_score_matrix(fixtures)])

    def strength_table(self) -> pd.DataFrame:
        if self.attack_ is None:
            return pd.DataFrame()
        return pd.DataFrame({
            "team": self.teams_,
            "attack": self.attack_,
            "defence": self.defence_,
        }).sort_values("attack", ascending=False).reset_index(drop=True)

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "half_life_days": self.cfg.half_life_days,
            "home_advantage_log": self.ha_,
            "rho": self.rho_,
            "ridge": self.ridge,
            "n_teams": len(self.teams_),
            "as_of": None if self.as_of_ is None else self.as_of_.strftime("%Y-%m-%d"),
        }
