"""Deterministic knockout-bracket resolution from *played* results only.

While the Monte-Carlo simulator estimates how likely each team is to reach each
round, this module answers a different, factual question: **given the results
that have actually happened, who is really in each knockout slot?**

It uses two sources of truth, in order of preference:

1. **Real knockout fixtures** from the live feed — once the official schedule
   assigns teams to a Round-of-32 match (and as later rounds are played), the
   fixture itself carries the real teams and the score.  This is what makes the
   bracket *advance* with the tournament.
2. **Structural resolution** — group winners/runners-up from the live standings,
   and the eight best third-placed teams allocated to their Round-of-32 slots
   using FIFA's allowed-group constraints (the same rule the simulator uses).
   This fills matchups *before* the feed lists the fixture, and labels every
   still-undecided slot.

Strictly no future information is used: a slot is only resolved when the results
that determine it are final.  This keeps the page honest and leakage-free.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass

from scipy.optimize import linear_sum_assignment

from wc2026.config import PATHS
from wc2026.data.tournament import Tournament
from wc2026.standings import current_group_standings
from wc2026.teams import canonical_name, team_code

ROUND_ORDER = ["R32", "R16", "QF", "SF", "THIRD_PLACE", "FINAL"]


@dataclass
class Slot:
    """A resolved (or still-pending) side of a knockout match."""
    team: str | None          # canonical team name, or None if undecided
    label: str                # human label shown when undecided ("Winner 89")
    sub: str | None = None    # secondary label ("Match 89", group list)


def _shootout_winners() -> dict[tuple[str, str, str], str]:
    """(date, home, away) -> winner, for ties decided on penalties."""
    path = PATHS.data_raw / "shootouts.csv"
    out: dict[tuple[str, str, str], str] = {}
    if not path.exists():
        return out
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out[(row["date"], canonical_name(row["home_team"]),
                     canonical_name(row["away_team"]))] = canonical_name(row["winner"])
            except Exception:
                continue
    return out


def _group_state(t: Tournament):
    """Per group: ranked teams + whether positions 1/2/3 are mathematically set."""
    standings = current_group_standings(t)
    winner: dict[str, str] = {}
    runner: dict[str, str] = {}
    third: dict[str, dict] = {}
    for gl, rows in standings.items():
        complete = len(rows) == 4 and all(r["played"] >= 3 for r in rows)
        if not complete:
            continue

        def key(r):
            return (r["points"], r["gd"], r["gf"])

        # Only treat a position as decided when it is strictly ahead of the next
        # team (we don't model head-to-head / fair-play / drawing of lots here).
        if key(rows[0]) > key(rows[1]):
            winner[gl] = rows[0]["team"]
        if key(rows[1]) > key(rows[2]):
            runner[gl] = rows[1]["team"]
        third[gl] = {"team": rows[2]["team"], "key": key(rows[2])}
    return standings, winner, runner, third


def _third_allocation(t: Tournament, third: dict[str, dict]) -> dict[int, str]:
    """Map each R32 third-place *match number* -> the real third-placed team.

    Returns {} unless all twelve thirds are known and the top-eight boundary is
    unambiguous, mirroring the simulator's constraint-respecting assignment.
    """
    if len(third) != 12:
        return {}
    ranked = sorted(third.items(), key=lambda kv: kv[1]["key"], reverse=True)
    # Need a clean cut between the 8th and 9th best third.
    if ranked[7][1]["key"] == ranked[8][1]["key"]:
        return {}
    top8 = ranked[:8]                          # [(group, {...}), ...]
    combo_groups = [g for g, _ in top8]

    slots = t.third_place_slots                # 8 dicts: match, allowed, opponent
    cost = [[1e6] * 8 for _ in range(8)]       # rows = slots, cols = combo position
    for si, s in enumerate(slots):
        for ci, g in enumerate(combo_groups):
            if g in s["allowed"]:
                cost[si][ci] = ci * 1e-3       # deterministic tiebreak
    r, c = linear_sum_assignment(cost)
    if sum(cost[i][j] for i, j in zip(r, c, strict=True)) >= 1e5:
        return {}                              # infeasible (shouldn't happen)
    out: dict[int, str] = {}
    for si, ci in zip(r, c, strict=True):
        out[slots[si]["match"]] = third[combo_groups[ci]]["team"]
    return out


def resolve_bracket(t: Tournament) -> dict[str, dict]:
    """Return ``{str(match_number): {...}}`` resolving every knockout match.

    Each entry carries the two sides (real team when known, else a label), and,
    when the matching fixture has been played, the score, winner and status.
    """
    standings, winner, runner, third = _group_state(t)
    third_by_match = _third_allocation(t, third)
    shootouts = _shootout_winners()

    # Index of real knockout fixtures by team pair (cross-group ties live-fed).
    knockout: dict[frozenset[str], dict] = {}
    for _, m in t.knockout_fixtures.iterrows():
        knockout[frozenset((m["home_team"], m["away_team"]))] = m

    resolved: dict[str, dict] = {}
    win_of: dict[int, str] = {}                 # match number -> winner team
    lose_of: dict[int, str] = {}

    def resolve_token(tok: str, match_no: int) -> Slot:
        kind = tok[0]
        if kind == "1":
            g = tok[1]
            return Slot(winner.get(g), f"Winner Group {g}", None)
        if kind == "2":
            g = tok[1]
            return Slot(runner.get(g), f"Runner-up {g}", None)
        if tok.startswith("3:"):
            # Filled from the real fixture (preferred) or allocation (fallback)
            # later; never let the predicted allocation override a real fixture.
            return Slot(None, "3rd place", tok[2:].replace("/", " / "))
        if kind == "W":
            n = int(tok[1:])
            return Slot(win_of.get(n), "Winner", f"Match {n}")
        if kind == "L":
            n = int(tok[1:])
            return Slot(lose_of.get(n), "Loser", f"Match {n}")
        return Slot(None, tok, None)

    for rnd in ROUND_ORDER:
        for spec in t.bracket.get(rnd, []):
            no = spec["match"]
            s1 = resolve_token(spec["slot1"], no)
            s2 = resolve_token(spec["slot2"], no)

            # A third-place R32 slot: prefer the real fixture (ground truth) —
            # if its opponent is known, the other team in that fixture *is* the
            # qualified third.  Fall back to the predicted allocation only when
            # no fixture exists yet.
            for known, unknown, tok in ((s1, s2, spec["slot2"]),
                                        (s2, s1, spec["slot1"])):
                if unknown.team is None and tok.startswith("3:"):
                    allowed = set(tok[2:].split("/"))
                    if known.team is not None:
                        for pair in knockout:
                            if known.team in pair:
                                other = next(iter(pair - {known.team}))
                                if t.group_of(other) in allowed:
                                    unknown.team = other
                                    break
                    if unknown.team is None:                # fixture not out yet
                        unknown.team = third_by_match.get(no)

            entry: dict = {
                "match": no, "round": rnd,
                "slot1": spec["slot1"], "slot2": spec["slot2"],
                "team1": _team_obj(s1), "team2": _team_obj(s2),
                "label1": s1.label, "sub1": s1.sub,
                "label2": s2.label, "sub2": s2.sub,
                "score1": None, "score2": None,
                "winner_code": None, "status": "pending", "date": None,
                "match_id": None,
            }

            if s1.team and s2.team:
                fx = knockout.get(frozenset((s1.team, s2.team)))
                if fx is not None:
                    entry["date"] = fx["date"].strftime("%Y-%m-%d")
                    entry["match_id"] = fx["match_id"]
                    if fx["status"] == "played":
                        hs, as_ = int(fx["home_score"]), int(fx["away_score"])
                        # Map the fixture's home/away onto our slot1/slot2 order.
                        if fx["home_team"] == s1.team:
                            entry["score1"], entry["score2"] = hs, as_
                        else:
                            entry["score1"], entry["score2"] = as_, hs
                        w = _winner_of(fx, hs, as_, shootouts)
                        if w is not None:
                            win_of[no] = w
                            lose_of[no] = s2.team if w == s1.team else s1.team
                            entry["winner_code"] = team_code(w)
                            entry["status"] = "played"
                        else:
                            entry["status"] = "played"   # drawn, shootout unknown
                    else:
                        entry["status"] = "scheduled"
            resolved[str(no)] = entry

    return resolved


def _team_obj(s: Slot) -> dict | None:
    if not s.team:
        return None
    return {"name": s.team, "code": team_code(s.team)}


def _winner_of(fx, hs: int, as_: int, shootouts) -> str | None:
    if hs > as_:
        return fx["home_team"]
    if as_ > hs:
        return fx["away_team"]
    # Level after regulation/extra time: decided on penalties.
    key = (fx["date"].strftime("%Y-%m-%d"), fx["home_team"], fx["away_team"])
    return shootouts.get(key)
