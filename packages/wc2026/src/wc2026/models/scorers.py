"""Anytime-goalscorer model.

A light, transparent layer on top of the match goal model.  We don't have squad
sheets, so we approximate each team's likely scorers from *who has actually been
scoring for them recently* (time-decayed), then split the team's expected goals
across those players and convert to an anytime-scorer probability.

For a fixture with team expected goals ``mu``:

    player_xg = share_p * mu            # share_p = decayed goals_p / decayed goals_team
    P(player scores >= 1) = 1 - exp(-player_xg)

Strictly historical: ``fit(cutoff)`` only uses goals on/before the cutoff date,
so attaching these to future fixtures introduces no leakage.  Own goals are
excluded; penalties count.  This cannot know injuries or squad omissions — it is
clearly an estimate and surfaces the currently-hot scorers.
"""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

from wc2026.config import PATHS
from wc2026.teams import canonical_name


def _norm_name(s: str) -> str:
    """Accent/case-insensitive key so 'Julián Álvarez' == 'Julian Alvarez'."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def load_goalscorers() -> pd.DataFrame:
    """Load the raw goalscorers feed (CC0, same source as results)."""
    path = PATHS.data_raw / "goalscorers.csv"
    if not path.exists():
        return pd.DataFrame(columns=["date", "team", "scorer", "own_goal", "penalty"])
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].copy()
    for c in ("own_goal", "penalty"):
        if c in df:
            df[c] = df[c].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    df["team"] = df["team"].map(canonical_name)
    df["scorer"] = df["scorer"].astype(str).str.strip()
    return df


@dataclass
class GoalscorerModel:
    half_life_days: float = 900.0       # ~2.5y decay on a player's scoring weight
    window_years: int = 6               # ignore goals older than this before cutoff
    min_team_goals: float = 1.0         # guard against tiny samples
    # team -> list[(scorer, decayed_weight)], team -> total decayed weight
    by_team: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    team_total: dict[str, float] = field(default_factory=dict)
    cutoff: pd.Timestamp | None = None

    def fit(self, goals: pd.DataFrame, cutoff: pd.Timestamp) -> GoalscorerModel:
        self.cutoff = pd.Timestamp(cutoff)
        lo = self.cutoff - pd.DateOffset(years=self.window_years)
        g = goals[(goals["date"] <= self.cutoff) & (goals["date"] >= lo)].copy()
        if "own_goal" in g:
            g = g[~g["own_goal"].astype(bool)]
        if len(g) == 0:
            return self
        age = (self.cutoff - g["date"]).dt.days.clip(lower=0)
        g["w"] = 0.5 ** (age / self.half_life_days)
        g["norm"] = g["scorer"].map(_norm_name)
        # weight per (team, normalised player); display name = most-weighted spelling
        totals = g.groupby(["team", "norm"])["w"].sum()
        disp = (g.groupby(["team", "norm", "scorer"])["w"].sum()
                  .reset_index().sort_values("w", ascending=False)
                  .drop_duplicates(["team", "norm"]).set_index(["team", "norm"])["scorer"])
        agg = totals.reset_index()
        agg["scorer"] = [disp.loc[(t, n)] for t, n in zip(agg["team"], agg["norm"], strict=True)]
        agg = agg.sort_values("w", ascending=False)
        for team, sub in agg.groupby("team"):
            self.by_team[team] = list(zip(sub["scorer"], sub["w"], strict=True))
            self.team_total[team] = float(sub["w"].sum())
        return self

    def scorers(self, team: str, team_xg: float, top_n: int = 10) -> list[dict]:
        """Anytime-scorer probabilities for a team given its expected goals."""
        team = canonical_name(team)
        players = self.by_team.get(team)
        total = self.team_total.get(team, 0.0)
        if not players or total < self.min_team_goals or team_xg <= 0:
            return []
        scored: list[tuple[float, str]] = []
        for scorer, w in players[: top_n * 2]:
            share = w / total
            player_xg = share * float(team_xg)
            p = 1.0 - math.exp(-player_xg)
            if p >= 0.02:                       # drop negligible long-shots
                scored.append((round(p, 4), scorer))
        scored.sort(reverse=True)
        return [{"player": s, "team": team, "prob": p} for p, s in scored[:top_n]]
