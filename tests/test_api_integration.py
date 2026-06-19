"""API integration tests via FastAPI TestClient.

These hit the real app against whatever artifacts exist. They assert the
contract (status codes, shapes, invariants) rather than specific numbers.
"""
import os

import pytest
from wc2026.config import PATHS

pytestmark = pytest.mark.skipif(
    not (PATHS.data_processed / "matches.parquet").exists(),
    reason="run `wc2026 ingest` first",
)


@pytest.fixture(scope="module")
def client():
    os.environ["WC2026_ADMIN_TOKEN"] = "testtoken"
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["played_group_matches"] + body["pending_group_matches"] == 72


def test_teams_endpoint(client):
    r = client.get("/api/teams")
    assert r.status_code == 200
    teams = r.json()["teams"]
    assert len(teams) == 48


def test_groups_endpoint(client):
    r = client.get("/api/groups")
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert len(groups) == 12
    for rows in groups.values():
        assert len(rows) == 4


def test_unknown_team_404(client):
    assert client.get("/api/teams/atlantis").status_code == 404


def test_bracket_structure(client):
    r = client.get("/api/tournament/bracket")
    assert r.status_code == 200
    assert len(r.json()["rounds"]["R32"]) == 16


def test_admin_requires_token(client):
    assert client.post("/api/admin/ingest").status_code == 401
    r = client.post("/api/admin/ingest", headers={"Authorization": "Bearer testtoken"})
    assert r.status_code in (202, 200)


@pytest.mark.skipif(
    not (PATHS.simulations / "latest.json").exists(), reason="run `wc2026 simulate` first"
)
def test_probabilities_sum_to_one(client):
    r = client.get("/api/tournament/probabilities")
    assert r.status_code == 200
    teams = r.json()["teams"]
    total = sum(t["p_champion"] for t in teams)
    assert abs(total - 1.0) < 1e-6
