# Data Card

## Dataset
martj42/international_results (**CC0**) — men's international football results,
1872-11-30 → present, including live FIFA World Cup 2026 fixtures/results.

## Size & shape (as ingested)
49,475 validated matches; 336 teams. Fields: date, teams, scores, tournament,
city, country, neutral flag. Derived: codes, confederations, importance weight,
status (played/scheduled), is_world_cup.

## Collection
Community-maintained from public match reports/official sources. We fetch the
published CSVs only (no scraping). The official 2026 group/bracket structure is
verified separately from FIFA/Wikipedia and stored as a resource.

## Quality & cleaning
Ingestion drops unparseable/pre-1872 dates, negative/impossible scores,
self-matches, and duplicate `(date, home, away)` (official feed prioritised).
Names normalised to canonical forms. Report: `data/processed/ingestion_report.json`.

## Known limitations / biases
- Friendlies are noisier and lower-stakes (down-weighted via importance + decay).
- Coverage/quality is thinner for older eras and minor nations (mitigated by the
  1990s+ training windows and time decay).
- No squad, injury, lineup, weather, or travel data.
- Community data can lag or contain occasional errors; the official feed wins on
  conflict.

## Sensitive data
None. Only team-level match facts; no personal data.

## License
CC0 (data). Engine code MIT.
