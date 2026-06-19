"""Live group standings computed from locked (played) results only.

This is the 'real table' shown on the groups page — it never simulates; it just
tallies points/goal-difference/goals from matches that have actually finished.
"""
from __future__ import annotations

from wc2026.data.tournament import Tournament


def _blank(team: str, group: str) -> dict:
    return {"team": team, "group": group, "played": 0, "won": 0, "drawn": 0,
            "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0}


def current_group_standings(t: Tournament) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for gl in sorted(t.groups):
        rows = {team: _blank(team, gl) for team in t.groups[gl]}
        for _, m in t.group_fixtures(gl).iterrows():
            if m["status"] != "played":
                continue
            h, a = m["home_team"], m["away_team"]
            hs, as_ = int(m["home_score"]), int(m["away_score"])
            for team, gf, ga in ((h, hs, as_), (a, as_, hs)):
                r = rows[team]
                r["played"] += 1
                r["gf"] += gf
                r["ga"] += ga
                r["gd"] = r["gf"] - r["ga"]
                if gf > ga:
                    r["won"] += 1
                    r["points"] += 3
                elif gf == ga:
                    r["drawn"] += 1
                    r["points"] += 1
                else:
                    r["lost"] += 1
        ranked = sorted(rows.values(),
                        key=lambda r: (r["points"], r["gd"], r["gf"]), reverse=True)
        for i, r in enumerate(ranked):
            r["position"] = i + 1
        out[gl] = ranked
    return out


def standings_with_probabilities(t: Tournament, sim_teams: list[dict] | None) -> dict[str, list[dict]]:
    """Merge live standings with simulation qualification probabilities."""
    base = current_group_standings(t)
    if not sim_teams:
        return base
    prob = {row["team"]: row for row in sim_teams}
    for rows in base.values():
        for r in rows:
            p = prob.get(r["team"], {})
            r["p_win_group"] = p.get("p_win_group")
            r["p_runner_up"] = p.get("p_runner_up")
            r["p_qualify_third"] = p.get("p_qualify_third")
            r["p_advance"] = round(
                (p.get("p_win_group") or 0) + (p.get("p_runner_up") or 0)
                + (p.get("p_qualify_third") or 0), 4) if p else None
    return base
