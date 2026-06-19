# Data Sources

## Primary — martj42/international_results (CC0)
- URL: https://github.com/martj42/international_results
- License: **CC0** (public domain) — free to use, no attribution required (we attribute anyway).
- Coverage: every men's international since 1872-11-30; **includes the live FIFA
  World Cup 2026 fixtures and results** (the reason finished matches can be locked
  and pending ones forecast).
- Files used: `results.csv` (date, teams, score, tournament, city, country,
  neutral), `shootouts.csv`, `goalscorers.csv`.
- As ingested here: 49,475 valid matches, 1872-11-30 → 2026-06-27.

## Official 2026 structure (verified, stored as a resource)
- `packages/wc2026/src/wc2026/resources/wc2026.json` — the 12 groups (A–L), the
  full bracket (matches 73–104) and the third-place slot constraints.
- Verified 2026-06-18 from the
  [2026 FIFA World Cup draw](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_draw)
  and [knockout stage](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage)
  (FIFA final draw, 2025-12-05). Group membership is cross-checked against the
  live fixtures at load time.

## Alternative / future adapters
- **football-data.org** — documented adapter (needs `FOOTBALL_DATA_API_KEY`); not
  required for the demo.
- **OpenFootball**, **StatsBomb Open Data** — candidate enrichments where licenses permit.

## Offline fallback
If `data/raw/results.csv` is absent, ingestion generates a small, deterministic
**synthetic** dataset tagged `source=SYNTHETIC-DEMO` so the whole pipeline runs
with no network. Clearly labelled; never mixed with real data.

## Canonical match schema (`data/processed/matches.parquet`)
`match_id, date, home_team, away_team, home_code, away_code, home_score,
away_score, tournament, match_stage, neutral_venue, host_team, city, country,
confederation_home, confederation_away, status, is_world_cup, tournament_weight,
source, ingested_at`.

## Validation on ingest
Drops/flags: unparseable or pre-1872 dates, negative/impossible scores,
self-matches, duplicate `(date, home, away)` (official feed wins). A JSON report
is written to `data/processed/ingestion_report.json`.

## Name normalisation
`teams.py` maps spellings/codes to canonical names (accent- and case-insensitive),
handling USA/United States, Korea Republic/South Korea, DR Congo/Congo DR,
Côte d'Ivoire/Ivory Coast, Czechia/Czech Republic, Curaçao/Curacao, etc.

## Licensing summary
Data CC0; engine code MIT. No scraping; only published datasets/files are fetched.
