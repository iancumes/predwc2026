# API Reference

Base URL: `http://localhost:8000`. Interactive OpenAPI docs at `/docs`,
schema at `/openapi.json`. All responses JSON. Read endpoints never error on
missing artifacts — they return a `demo_mode` signal instead.

## Meta
- `GET /health` → status, model, data cutoff, n_sims, played/pending counts.

## Teams
- `GET /api/teams` → 48 teams with group, confederation, champion/win-group probs.
- `GET /api/teams/{code}` → detail: tournament probabilities, group fixtures, recent results. 404 if unknown.

## Matches
- `GET /api/matches?group=A&status=scheduled&team=brazil` → fixtures with 1X2.
- `GET /api/matches/{match_id}` → match detail + frozen prediction.
- `GET /api/matches/{match_id}/prediction` → the frozen prediction (1X2, xG, scorelines, factors). 404 if none.

## Groups
- `GET /api/groups` → all 12 live tables + qualification probabilities.
- `GET /api/groups/{group_id}` → one group.

## Tournament
- `GET /api/tournament/probabilities` → per-team round-reach + champion probs (+ n_sims, seed, model).
- `GET /api/tournament/bracket` → official slot structure + per-team round-reach probs.

## Model
- `GET /api/model/metrics` → backtest overall + slices, ensemble weights, calibration, track record.
- `GET /api/model/calibration` → reliability-curve data (pooled 1X2, test set).

## Actions
- `POST /api/simulations` `{ "n_sims": 50000, "seed": 20260611 }` → fresh simulation (1000–200000 sims).
- `POST /api/admin/ingest` — **requires** `Authorization: Bearer $WC2026_ADMIN_TOKEN`; runs in background (202).
- `POST /api/admin/train` — same guard; background (202).
- `GET /api/admin/jobs` — background job status (guarded).

## Errors & conventions
Standard HTTP codes: 200 ok, 202 accepted (admin jobs), 401 (bad/missing admin
token), 404 (unknown resource), 503 (admin disabled — no token configured).
Probabilities are returned in `[home, draw, away]` order and sum to 1 within
tolerance. Admin jobs are idempotent (a second concurrent call returns
`already_running`).

## Example
```bash
curl localhost:8000/api/tournament/probabilities | jq '.teams[0]'
curl -X POST localhost:8000/api/admin/train -H "Authorization: Bearer $WC2026_ADMIN_TOKEN"
```
