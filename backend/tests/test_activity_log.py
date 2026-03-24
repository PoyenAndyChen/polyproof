"""Tests for activity log recording and retrieval."""

import pytest
from httpx import AsyncClient


@pytest.fixture
def _disable_rate_limit(monkeypatch):
    monkeypatch.setattr("app.api.rate_limit.ip_limiter.enabled", False)
    monkeypatch.setattr("app.api.rate_limit.auth_limiter.enabled", False)


pytestmark = pytest.mark.usefixtures("_disable_rate_limit")


async def test_fill_event_recorded(
    client: AsyncClient, seed_agent, seed_project, mock_lean_pass
):
    """Submitting a fill records a 'fill' activity event."""
    sorry = seed_project["sorries"][0]
    project_id = str(seed_project["project"].id)
    headers = {"Authorization": f"Bearer {seed_agent['api_key']}"}

    await client.post(
        f"/api/v1/sorries/{sorry.id}/fill",
        headers=headers,
        json={
            "tactics": "simp [test_theorem_0]",
            "description": "Proved by simplification using the definition.",
        },
    )

    resp = await client.get(f"/api/v1/projects/{project_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    event_types = [e["event_type"] for e in data["events"]]
    assert "fill" in event_types

    # Verify the fill event has agent info
    fill_event = next(e for e in data["events"] if e["event_type"] == "fill")
    assert fill_event["agent"] is not None
    assert fill_event["agent"]["handle"].startswith("test_agent")
    assert fill_event["sorry_id"] == str(sorry.id)


async def test_comment_event_recorded(client: AsyncClient, seed_agent, seed_project):
    """Posting a comment records a 'comment' activity event."""
    sorry = seed_project["sorries"][0]
    project_id = str(seed_project["project"].id)
    headers = {"Authorization": f"Bearer {seed_agent['api_key']}"}

    await client.post(
        f"/api/v1/sorries/{sorry.id}/comments",
        headers=headers,
        json={"body": "Test comment for activity log"},
    )

    resp = await client.get(f"/api/v1/projects/{project_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    event_types = [e["event_type"] for e in data["events"]]
    assert "comment" in event_types


async def test_activity_feed_pagination(client: AsyncClient, seed_agent, seed_project):
    """Activity feed supports limit and offset."""
    project_id = str(seed_project["project"].id)
    sorry = seed_project["sorries"][0]
    headers = {"Authorization": f"Bearer {seed_agent['api_key']}"}

    # Create multiple events
    for i in range(5):
        await client.post(
            f"/api/v1/sorries/{sorry.id}/comments",
            headers=headers,
            json={"body": f"Comment {i}"},
        )

    resp = await client.get(f"/api/v1/projects/{project_id}/activity?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["total"] >= 5


async def test_activity_feed_empty_project(client: AsyncClient, seed_project):
    """Activity feed for a project with no activity returns empty."""
    project_id = str(seed_project["project"].id)
    resp = await client.get(f"/api/v1/projects/{project_id}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 0
