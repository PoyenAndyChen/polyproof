"""Tests for sorry detail and fill submission."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
def _disable_rate_limit(monkeypatch):
    monkeypatch.setattr("app.api.rate_limit.ip_limiter.enabled", False)
    monkeypatch.setattr("app.api.rate_limit.auth_limiter.enabled", False)


pytestmark = pytest.mark.usefixtures("_disable_rate_limit")


async def test_get_sorry_detail(client: AsyncClient, seed_project):
    sorry = seed_project["sorries"][0]
    resp = await client.get(f"/api/v1/sorries/{sorry.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["declaration_name"] == "test_theorem_0"
    assert data["goal_state"] == "⊢ test_goal_0 = true"
    assert data["status"] == "open"
    assert "children" in data
    assert "parent_chain" in data


async def test_get_sorry_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/sorries/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_fill_sorry(client: AsyncClient, seed_project, seed_agent, mock_lean_pass):
    sorry = seed_project["sorries"][0]
    resp = await client.post(
        f"/api/v1/sorries/{sorry.id}/fill",
        json={
            "tactics": "simp [test_theorem_0]",
            "description": "Proved by simplification using the definition.",
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert "job_id" in data


async def test_fill_sorry_no_auth(client: AsyncClient, seed_project):
    sorry = seed_project["sorries"][0]
    resp = await client.post(
        f"/api/v1/sorries/{sorry.id}/fill",
        json={
            "tactics": "simp",
            "description": "Test fill without auth.",
        },
    )
    assert resp.status_code == 401


async def test_fill_sorry_short_description(
    client: AsyncClient, seed_project, seed_agent, mock_lean_pass
):
    sorry = seed_project["sorries"][0]
    resp = await client.post(
        f"/api/v1/sorries/{sorry.id}/fill",
        json={
            "tactics": "simp",
            "description": "Too short",
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert resp.status_code == 422  # description min 20 chars
