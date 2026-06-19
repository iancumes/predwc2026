"""Common model interface and score-matrix → market-probability helpers.

Outcome convention everywhere: index 0 = home win, 1 = draw, 2 = away win.
A "score matrix" M has shape (G+1, G+1) where M[i, j] = P(home scores i, away
scores j).  All market quantities (1X2, totals, BTTS, exact scores) are derived
from that single object so every model is mutually consistent.
"""
from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HOME, DRAW, AWAY = 0, 1, 2
OUTCOME_LABELS = ["home_win", "draw", "away_win"]


def result_index(home_score: float, away_score: float) -> int:
    if home_score > away_score:
        return HOME
    if home_score == away_score:
        return DRAW
    return AWAY


def probs_from_matrix(m: np.ndarray) -> np.ndarray:
    """1X2 probabilities from a score matrix."""
    total = m.sum()
    if total <= 0:
        return np.array([1 / 3, 1 / 3, 1 / 3])
    m = m / total
    p_home = np.tril(m, -1).sum()   # home > away
    p_draw = np.trace(m)
    p_away = np.triu(m, 1).sum()    # away > home
    return np.array([p_home, p_draw, p_away])


# Over/under lines we publish (P(total goals > line)).
GOAL_LINES = (0.5, 1.5, 2.5, 3.5)
# Number of explicit total-goals buckets (last is a "k+" tail).
TOTAL_GOALS_BUCKETS = 7


@dataclass
class MarketProbabilities:
    home_win: float
    draw: float
    away_win: float
    over_2_5: float
    under_2_5: float
    btts_yes: float
    btts_no: float
    expected_home_goals: float
    expected_away_goals: float
    top_scorelines: list[tuple[str, float]]
    # --- richer goal markets (all derived from the same score matrix) ------
    over_under: dict[str, float] = field(default_factory=dict)
    total_goals_dist: list[float] = field(default_factory=list)
    expected_total_goals: float = 0.0
    most_likely_score: str = ""
    home_clean_sheet: float = 0.0
    away_clean_sheet: float = 0.0
    home_win_to_nil: float = 0.0
    away_win_to_nil: float = 0.0

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["top_scorelines"] = [{"score": s, "prob": p} for s, p in self.top_scorelines]
        return d


def market_probabilities(m: np.ndarray, top_n: int = 6) -> MarketProbabilities:
    """Full set of betting-style markets derived from one score matrix."""
    total = m.sum()
    m = m / total if total > 0 else m
    g = m.shape[0]
    idx = np.arange(g)
    ph, pd_, pa = probs_from_matrix(m)

    # total-goals distribution: P(home + away == t) along anti-diagonals
    tot_max = 2 * (g - 1)
    dist_full = np.zeros(tot_max + 1)
    for i in range(g):
        for j in range(g):
            dist_full[i + j] += m[i, j]

    # over/under lines from the cumulative tail of the total-goals pmf
    over_under: dict[str, float] = {}
    for line in GOAL_LINES:
        thresh = int(np.floor(line)) + 1            # total strictly greater than line
        over_under[str(line)] = float(dist_full[thresh:].sum())
    over = over_under["2.5"]
    under = 1.0 - over

    # bucketed distribution for the UI: 0,1,..,(B-2),(B-1)+  tail
    b = TOTAL_GOALS_BUCKETS
    bucketed: list[float] = [float(x) for x in dist_full[: b - 1]]
    bucketed.append(float(dist_full[b - 1:].sum()))

    # both teams to score
    btts_no = m[0, :].sum() + m[:, 0].sum() - m[0, 0]
    btts_yes = 1.0 - btts_no

    # clean sheets and win-to-nil
    home_clean_sheet = float(m[:, 0].sum())          # away scores 0
    away_clean_sheet = float(m[0, :].sum())          # home scores 0
    home_win_to_nil = float(np.tril(m, -1)[:, 0].sum())   # home wins, away 0
    away_win_to_nil = float(np.triu(m, 1)[0, :].sum())    # away wins, home 0

    exp_home = float((m.sum(axis=1) * idx).sum())
    exp_away = float((m.sum(axis=0) * idx).sum())

    flat = [((i, j), float(m[i, j])) for i in range(g) for j in range(g)]
    flat.sort(key=lambda kv: kv[1], reverse=True)
    top = [(f"{i}-{j}", p) for (i, j), p in flat[:top_n]]

    return MarketProbabilities(
        home_win=float(ph), draw=float(pd_), away_win=float(pa),
        over_2_5=float(over), under_2_5=float(under),
        btts_yes=float(btts_yes), btts_no=float(btts_no),
        expected_home_goals=exp_home, expected_away_goals=exp_away,
        top_scorelines=top,
        over_under={k: round(v, 4) for k, v in over_under.items()},
        total_goals_dist=[round(x, 4) for x in bucketed],
        expected_total_goals=exp_home + exp_away,
        most_likely_score=top[0][0] if top else "",
        home_clean_sheet=home_clean_sheet, away_clean_sheet=away_clean_sheet,
        home_win_to_nil=home_win_to_nil, away_win_to_nil=away_win_to_nil,
    )


class MatchModel(ABC):
    """Abstract base class: every model implements this interface."""

    name: str = "base"

    @abstractmethod
    def fit(self, matches: pd.DataFrame) -> MatchModel:
        ...

    @abstractmethod
    def predict_proba(self, fixtures: pd.DataFrame) -> np.ndarray:
        """Return (n, 3) array of [home_win, draw, away_win] probabilities."""
        ...

    def predict_score_matrix(self, fixtures: pd.DataFrame) -> list[np.ndarray]:
        """Optional: per-fixture score matrices.  Default: not supported."""
        raise NotImplementedError(f"{self.name} does not produce score matrices")

    def predict_expected_goals(self, fixtures: pd.DataFrame) -> np.ndarray:
        mats = self.predict_score_matrix(fixtures)
        out = np.zeros((len(mats), 2))
        for k, m in enumerate(mats):
            mp = market_probabilities(m)
            out[k] = [mp.expected_home_goals, mp.expected_away_goals]
        return out

    def metadata(self) -> dict:
        return {"name": self.name}

    def save(self, path) -> None:
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @classmethod
    def load(cls, path) -> MatchModel:
        with open(path, "rb") as fh:
            return pickle.load(fh)


def normalise_rows(p: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    p = np.clip(p, eps, None)
    return p / p.sum(axis=1, keepdims=True)
