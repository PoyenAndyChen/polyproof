"""Tests for project creation, listing, and detail endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.fixture
def _disable_rate_limit(monkeypatch):
    monkeypatch.setattr("app.api.rate_limit.ip_limiter.enabled", False)
    monkeypatch.setattr("app.api.rate_limit.auth_limiter.enabled", False)


pytestmark = pytest.mark.usefixtures("_disable_rate_limit")


async def test_create_project_admin(client: AsyncClient, mock_lean_pass):
    resp = await client.post(
        "/api/v1/projects",
        json={
            "title": "Test Carleson",
            "description": "Test project",
            "upstream_repo": "https://github.com/fpvandoorn/carleson",
            "fork_repo": "https://github.com/polyproof/carleson",
            "lean_toolchain": "leanprover/lean4:v4.28.0",
            "workspace_path": "/opt/polyproof/projects/carleson",
            "tracked_files": ["Carleson/ToMathlib/Analysis/Test.lean"],
        },
        headers={"Authorization": f"Bearer {settings.ADMIN_API_KEY}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Carleson"
    assert "id" in data


async def test_create_project_non_admin(client: AsyncClient, seed_agent):
    resp = await client.post(
        "/api/v1/projects",
        json={
            "title": "Unauthorized",
            "description": "Should fail",
            "upstream_repo": "https://github.com/test/test",
            "fork_repo": "https://github.com/polyproof/test",
            "lean_toolchain": "leanprover/lean4:v4.28.0",
            "workspace_path": "/opt/test",
            "tracked_files": ["Test.lean"],
        },
        headers={"Authorization": f"Bearer {seed_agent['api_key']}"},
    )
    assert resp.status_code == 401


async def test_list_projects(client: AsyncClient, seed_project):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["projects"]) >= 1


async def test_get_project_detail(client: AsyncClient, seed_project):
    project_id = str(seed_project["project"].id)
    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Project: Carleson"
    assert "files" in data
    assert "open_sorries" in data


async def test_get_project_sorries(client: AsyncClient, seed_project):
    project_id = str(seed_project["project"].id)
    resp = await client.get(f"/api/v1/projects/{project_id}/sorries")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["sorries"]) == 3
    # Each sorry should have goal_state
    for s in data["sorries"]:
        assert "goal_state" in s
        assert "declaration_name" in s


async def test_get_project_overview(client: AsyncClient, seed_project):
    project_id = str(seed_project["project"].id)
    resp = await client.get(f"/api/v1/projects/{project_id}/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "project" in data
    assert "sorries" in data


async def test_get_project_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert resp.status_code == 404
