"""Tests for verify and freeform verify endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
def _disable_rate_limit(monkeypatch):
    monkeypatch.setattr("app.api.rate_limit.ip_limiter.enabled", False)
    monkeypatch.setattr("app.api.rate_limit.auth_limiter.enabled", False)


pytestmark = pytest.mark.usefixtures("_disable_rate_limit")


async def test_verify_with_sorry_id(
    client: AsyncClient, seed_project, seed_agent, mock_lean_pass
):
    sorry = seed_project["sorries"][0]
    resp = await client.post(
        "/api/v1/verify",
        json={
            "sorry_id": str(sorry.id),
            "tactics": "simp\nsorry",
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("passed", "rejected")


async def test_verify_freeform(
    client: AsyncClient, seed_project, seed_agent, mock_lean_pass
):
    project = seed_project["project"]
    resp = await client.post(
        "/api/v1/verify/freeform",
        json={
            "project_id": str(project.id),
            "code": "#check Nat.add_comm",
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("passed", "rejected")


async def test_verify_no_auth(client: AsyncClient, seed_project):
    sorry = seed_project["sorries"][0]
    resp = await client.post(
        "/api/v1/verify",
        json={
            "sorry_id": str(sorry.id),
            "tactics": "simp",
        },
    )
    assert resp.status_code == 401
