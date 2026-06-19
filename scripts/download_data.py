"""Fetch the latest international results and merge them into ``data/raw``.

Source: ``martj42/international_results`` (CC0, no API key) — every men's
international since 1872, updated continuously as matches are played, plus the
goalscorers feed used by the anytime-scorer model.

Crucially this *merges* rather than overwrites, keyed on
``(date, home_team, away_team)``:

* a row that already has a real score is kept (the official feed wins ties), so
  as the upstream feed reports a World Cup match, that result fills into our
  fixture row and the next ``ingest`` flips it from *scheduled* to *played*;
* fixtures the feed hasn't played yet (our committed 2026 schedule) are never
  dropped.

So the tournament schedule is preserved while real results progressively replace
any placeholder rows — exactly what a daily refresh needs.  Network failure is
non-fatal: we keep whatever is already on disk and exit 0 so the pipeline can
still run offline.
"""
from __future__ import annotations

import ssl
import sys
import urllib.request
from io import StringIO
from pathlib import Path

import pandas as pd


def _ssl_context() -> ssl.SSLContext | None:
    """Prefer certifi's CA bundle (robust on macOS/minimal images)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://raw.githubusercontent.com/martj42/international_results/master"
FILES = {
    "results.csv": f"{BASE}/results.csv",
    "goalscorers.csv": f"{BASE}/goalscorers.csv",
    "shootouts.csv": f"{BASE}/shootouts.csv",
}
KEY = ["date", "home_team", "away_team"]


def _fetch(url: str, timeout: int = 60) -> pd.DataFrame | None:
    req = urllib.request.Request(url, headers={"User-Agent": "wc2026-updater"})
    ctx = _ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:  # noqa: S310
            return pd.read_csv(StringIO(r.read().decode("utf-8")))
    except Exception as e:  # pragma: no cover - network dependent
        print(f"[download] WARN could not fetch {url}: {e}")
        return None


def _has_score(df: pd.DataFrame) -> pd.Series:
    h = pd.to_numeric(df.get("home_score"), errors="coerce")
    a = pd.to_numeric(df.get("away_score"), errors="coerce")
    return h.notna() & a.notna()


def _merge_results(old: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Union on KEY; prefer rows that carry a real score (official feed on ties)."""
    if old is None or len(old) == 0:
        return new
    old = old.copy()
    new = new.copy()
    old["_played"] = _has_score(old)
    new["_played"] = _has_score(new)
    old["_src"] = 0          # local / schedule
    new["_src"] = 1          # upstream feed (wins ties)
    both = pd.concat([old, new], ignore_index=True)
    # rank: played first, then upstream; keep the best row per fixture key
    both = both.sort_values(["_played", "_src"], ascending=False)
    merged = both.drop_duplicates(subset=KEY, keep="first")
    merged = merged.drop(columns=["_played", "_src"]).sort_values("date")
    return merged.reset_index(drop=True)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    any_ok = False

    # --- results: merge to preserve the schedule -------------------------------
    new_results = _fetch(FILES["results.csv"])
    if new_results is not None:
        path = RAW / "results.csv"
        old = pd.read_csv(path) if path.exists() else None
        merged = _merge_results(old, new_results)
        merged.to_csv(path, index=False)
        any_ok = True
        played = int(_has_score(merged).sum())
        print(f"[download] results.csv: {len(merged)} rows ({played} played) "
              f"-> {path}")

    # --- goalscorers / shootouts: union, newest wins ---------------------------
    for name in ("goalscorers.csv", "shootouts.csv"):
        new_df = _fetch(FILES[name])
        if new_df is None:
            continue
        path = RAW / name
        if path.exists():
            old = pd.read_csv(path)
            key = [c for c in ("date", "home_team", "away_team", "scorer", "minute")
                   if c in new_df.columns]
            new_df = (pd.concat([old, new_df], ignore_index=True)
                        .drop_duplicates(subset=key or None, keep="last"))
        new_df.to_csv(path, index=False)
        any_ok = True
        print(f"[download] {name}: {len(new_df)} rows -> {path}")

    if not any_ok:
        print("[download] no files fetched (offline?); keeping existing data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
