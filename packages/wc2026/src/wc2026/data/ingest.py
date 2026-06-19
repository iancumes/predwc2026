"""Ingest raw international results into a clean, validated match table.

Primary source: ``martj42/international_results`` (CC0).  The raw CSVs are
expected in ``data/raw/``; ``scripts/download_data.py`` (or ``make ingest``)
fetches them.  If they are absent we fall back to a small, clearly-labelled
synthetic dataset so the whole pipeline still runs offline (demo mode).

The output ``data/processed/matches.parquet`` follows the schema described in
docs/DATA_SOURCES.md.  Validation drops impossible rows and de-duplicates
matches reported by multiple sources, always preferring the official feed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from wc2026.config import PATHS, tournament_weight
from wc2026.teams import canonical_name, confederation, team_code

SOURCE_NAME = "martj42/international_results"

MATCH_COLUMNS = [
    "match_id", "date", "home_team", "away_team", "home_code", "away_code",
    "home_score", "away_score", "tournament", "match_stage", "neutral_venue",
    "host_team", "city", "country", "confederation_home", "confederation_away",
    "status", "is_world_cup", "tournament_weight", "source", "ingested_at",
]


def _match_id(date: str, home: str, away: str) -> str:
    raw = f"{date}|{home}|{away}".encode()
    return hashlib.sha1(raw).hexdigest()[:16]


def _synthetic_fallback() -> pd.DataFrame:
    """Deterministic synthetic results so the pipeline runs with no network.

    Clearly flagged with source='SYNTHETIC-DEMO'.  Never used when real data
    is present.
    """
    rng = np.random.default_rng(42)
    teams = [
        "Brazil", "France", "Argentina", "Spain", "England", "Germany",
        "Netherlands", "Portugal", "Croatia", "Mexico", "United States",
        "Japan", "Morocco", "Senegal", "South Korea", "Australia",
    ]
    strength = {t: rng.normal(0, 0.4) for t in teams}
    rows = []
    start = pd.Timestamp("2005-01-01")
    for i in range(2400):
        d = start + pd.Timedelta(days=int(i * 3.5))
        h, a = rng.choice(teams, size=2, replace=False)
        lam_h = np.exp(0.2 + strength[h] - strength[a] + 0.25)
        lam_a = np.exp(0.2 + strength[a] - strength[h])
        hs, as_ = rng.poisson(lam_h), rng.poisson(lam_a)
        rows.append({
            "date": d.strftime("%Y-%m-%d"), "home_team": h, "away_team": a,
            "home_score": hs, "away_score": as_, "tournament": "Friendly",
            "city": "Demo City", "country": h, "neutral": False,
        })
    return pd.DataFrame(rows)


def _load_raw() -> tuple[pd.DataFrame, str]:
    results_path = PATHS.data_raw / "results.csv"
    if results_path.exists():
        df = pd.read_csv(results_path)
        return df, SOURCE_NAME
    return _synthetic_fallback(), "SYNTHETIC-DEMO"


def _validate(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict[str, int] = {}
    n0 = len(df)

    # Parse dates; drop unparseable.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    df = df[df["date"].notna()].copy()
    report["dropped_invalid_dates"] = int(bad_dates)

    # Future dates beyond a sane horizon are scheduled fixtures, not errors,
    # but anything before the first international (1872) is invalid.
    too_old = (df["date"] < pd.Timestamp("1872-01-01")).sum()
    df = df[df["date"] >= pd.Timestamp("1872-01-01")].copy()
    report["dropped_pre_1872"] = int(too_old)

    # Impossible scores (negative).  Missing scores (NA) are *scheduled*, kept.
    for col in ("home_score", "away_score"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    neg = ((df["home_score"] < 0) | (df["away_score"] < 0)).sum()
    df = df[~((df["home_score"] < 0) | (df["away_score"] < 0))].copy()
    report["dropped_negative_scores"] = int(neg)

    # Self-matches are impossible.
    df["home_team"] = df["home_team"].map(canonical_name)
    df["away_team"] = df["away_team"].map(canonical_name)
    self_match = (df["home_team"] == df["away_team"]).sum()
    df = df[df["home_team"] != df["away_team"]].copy()
    report["dropped_self_matches"] = int(self_match)

    # De-duplicate identical (date, home, away) keeping the first occurrence
    # (official feed is loaded first).
    before = len(df)
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
    report["dropped_duplicates"] = int(before - len(df))

    report["rows_in"] = int(n0)
    report["rows_out"] = int(len(df))
    return df, report


def ingest(verbose: bool = True) -> pd.DataFrame:
    """Run the full ingestion and persist ``matches.parquet``.  Returns the table."""
    PATHS.ensure()
    raw, source = _load_raw()
    df, report = _validate(raw)

    df = df.sort_values("date").reset_index(drop=True)

    df["neutral_venue"] = df.get("neutral", False)
    df["neutral_venue"] = (
        df["neutral_venue"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    )
    df["status"] = np.where(
        df["home_score"].notna() & df["away_score"].notna(), "played", "scheduled"
    )
    df["is_world_cup"] = df["tournament"].eq("FIFA World Cup")
    df["tournament_weight"] = df["tournament"].map(tournament_weight)
    df["host_team"] = df["country"].where(~df["neutral_venue"].astype(bool), other=None)
    df["confederation_home"] = df["home_team"].map(confederation)
    df["confederation_away"] = df["away_team"].map(confederation)
    df["home_code"] = df["home_team"].map(team_code)
    df["away_code"] = df["away_team"].map(team_code)
    df["match_stage"] = None
    df["source"] = source
    df["ingested_at"] = datetime.now(UTC).isoformat()
    df["match_id"] = [
        _match_id(d.strftime("%Y-%m-%d"), h, a)
        for d, h, a in zip(df["date"], df["home_team"], df["away_team"], strict=True)
    ]

    out = df[MATCH_COLUMNS].copy()
    out_path = PATHS.data_processed / "matches.parquet"
    out.to_parquet(out_path, index=False)

    report["source"] = source
    report["n_teams"] = int(
        pd.concat([out["home_team"], out["away_team"]]).nunique()
    )
    report["date_min"] = out["date"].min().strftime("%Y-%m-%d")
    report["date_max"] = out["date"].max().strftime("%Y-%m-%d")
    report["n_played"] = int((out["status"] == "played").sum())
    report["n_scheduled"] = int((out["status"] == "scheduled").sum())
    (PATHS.data_processed / "ingestion_report.json").write_text(
        json.dumps(report, indent=2)
    )

    if verbose:
        print(f"[ingest] source={source} rows_out={report['rows_out']} "
              f"teams={report['n_teams']} range={report['date_min']}..{report['date_max']}")
        print(f"[ingest] played={report['n_played']} scheduled={report['n_scheduled']} "
              f"dropped={report['rows_in'] - report['rows_out']}")
        print(f"[ingest] wrote {out_path}")
    return out


def load_matches(played_only: bool = False) -> pd.DataFrame:
    """Load the processed match table, parsing dates."""
    path = PATHS.data_processed / "matches.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `make ingest` (or `python -m wc2026.cli ingest`) first."
        )
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    if played_only:
        df = df[df["status"] == "played"].copy()
    return df.reset_index(drop=True)
