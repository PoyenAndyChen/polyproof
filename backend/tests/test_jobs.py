"""Tests for job status retrieval."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
def _disable_rate_limit(monkeypatch):
    monkeypatch.setattr("app.api.rate_limit.ip_limiter.enabled", False)
    monkeypatch.setattr("app.api.rate_limit.auth_limiter.enabled", False)


pytestmark = pytest.mark.usefixtures("_disable_rate_limit")


async def test_get_job_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/jobs/{uuid4()}")
    assert resp.status_code == 404


async def test_get_job_after_fill(
    client: AsyncClient, seed_project, seed_agent, mock_lean_pass
):
    sorry = seed_project["sorries"][0]
    # Submit a fill
    fill_resp = await client.post(
        f"/api/v1/sorries/{sorry.id}/fill",
        json={
            "tactics": "simp [test_theorem_0]",
            "description": "Proved by simplification using the definition.",
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert fill_resp.status_code == 202
    job_id = fill_resp.json()["job_id"]

    # Get job status
    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("queued", "compiling", "merged", "failed", "superseded")
    assert data["job_type"] == "fill"
