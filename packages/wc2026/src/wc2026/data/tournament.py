"""FIFA World Cup 2026 tournament structure.

Combines the *official* immutable structure (group letters, bracket slots,
third-place constraints — verified from FIFA/Wikipedia and stored in
``resources/wc2026.json``) with the *live* fixtures and results coming from the
ingested data feed.  Group membership from the resource file is cross-checked
against the fixtures so a data update that changes a team is caught loudly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources

import pandas as pd

from wc2026.data.ingest import load_matches
from wc2026.teams import canonical_name


def _load_structure() -> dict:
    with resources.files("wc2026.resources").joinpath("wc2026.json").open() as fh:
        return json.load(fh)


@dataclass
class Tournament:
    groups: dict[str, list[str]]                 # 'A' -> [team, team, team, team]
    hosts: list[str]
    bracket: dict[str, list[dict]]               # round -> list of {match, slot1, slot2}
    fixtures: pd.DataFrame                        # the 72 group-stage matches (live)
    team_group: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.team_group = {
            t: g for g, teams in self.groups.items() for t in teams
        }

    # -- structure helpers --------------------------------------------------
    @property
    def teams(self) -> list[str]:
        return [t for g in sorted(self.groups) for t in self.groups[g]]

    def group_of(self, team: str) -> str | None:
        return self.team_group.get(canonical_name(team))

    @property
    def third_place_slots(self) -> list[dict]:
        """R32 slots that take a best third-placed team, with allowed groups."""
        out = []
        for m in self.bracket["R32"]:
            for key in ("slot1", "slot2"):
                tok = m[key]
                if tok.startswith("3:"):
                    out.append({
                        "match": m["match"],
                        "allowed": tok[2:].split("/"),
                        "opponent": m["slot1"] if key == "slot2" else m["slot2"],
                    })
        return out

    # -- live state ---------------------------------------------------------
    def group_fixtures(self, group: str) -> pd.DataFrame:
        teams = set(self.groups[group])
        f = self.fixtures
        mask = f["home_team"].isin(teams) & f["away_team"].isin(teams)
        return f[mask].sort_values("date").reset_index(drop=True)

    @property
    def played(self) -> pd.DataFrame:
        return self.fixtures[self.fixtures["status"] == "played"].reset_index(drop=True)

    @property
    def pending(self) -> pd.DataFrame:
        return self.fixtures[self.fixtures["status"] != "played"].reset_index(drop=True)

    def validate(self) -> list[str]:
        """Return a list of integrity warnings (empty == all good)."""
        warnings: list[str] = []
        # 12 groups of 4
        if len(self.groups) != 12:
            warnings.append(f"expected 12 groups, found {len(self.groups)}")
        for g, teams in self.groups.items():
            if len(teams) != 4:
                warnings.append(f"group {g} has {len(teams)} teams")
        # every fixture connects two teams of the same official group
        for _, r in self.fixtures.iterrows():
            gh, ga = self.group_of(r["home_team"]), self.group_of(r["away_team"])
            if gh is None or ga is None:
                warnings.append(f"unknown team in fixture {r['home_team']} v {r['away_team']}")
            elif gh != ga:
                warnings.append(
                    f"cross-group fixture {r['home_team']}({gh}) v {r['away_team']}({ga})"
                )
        return warnings


def load_tournament() -> Tournament:
    struct = _load_structure()
    groups = {g: [canonical_name(t) for t in teams] for g, teams in struct["groups"].items()}

    matches = load_matches()
    wc = matches[
        matches["is_world_cup"] & (matches["date"] >= pd.Timestamp("2026-01-01"))
    ].copy()
    # Keep only the 72 group-stage fixtures (both teams belong to a group).
    members = {t for teams in groups.values() for t in teams}
    wc = wc[wc["home_team"].isin(members) & wc["away_team"].isin(members)].copy()
    wc = wc.sort_values("date").reset_index(drop=True)

    return Tournament(
        groups=groups,
        hosts=[canonical_name(t) for t in struct["hosts"]],
        bracket=struct["bracket"],
        fixtures=wc,
    )
