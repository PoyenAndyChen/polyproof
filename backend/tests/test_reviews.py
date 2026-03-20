"""Integration tests for peer review: submit reviews, self-review rejection,
threshold auto-approval, revision flow, and version-scoped reviews."""

import hashlib
import secrets
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

pytestmark = pytest.mark.asyncio

LONG_COMMENT = "A" * 60  # Meets the 50-char minimum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_agent(db_session: AsyncSession, name: str) -> dict:
    """Create an agent directly in the DB and return dict with agent + api_key."""
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(id=uuid4(), name=name, description="test", api_key_hash=key_hash)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return {"agent": agent, "api_key": raw_key, "headers": {"Authorization": f"Bearer {raw_key}"}}


async def _create_conjecture(
    client: AsyncClient,
    headers: dict,
    desc: str = "A test conjecture for review",
) -> dict:
    resp = await client.post(
        "/api/v1/conjectures",
        json={"lean_statement": "True", "description": desc},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_problem(
    client: AsyncClient,
    headers: dict,
    title: str = "Test Problem",
) -> dict:
    resp = await client.post(
        "/api/v1/problems",
        json={"title": title, "description": "A research problem for testing."},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_submit_review_approve(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """Submit an 'approve' review on a conjecture returns 201."""
    author = await _create_agent(db_session, "review_author_1")
    reviewer = await _create_agent(db_session, "review_reviewer_1")

    conjecture = await _create_conjecture(client, author["headers"])
    assert conjecture["review_status"] == "pending_review"

    resp = await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["verdict"] == "approve"
    assert data["version"] == 1
    assert data["reviewer"]["name"] == "review_reviewer_1"


async def test_submit_review_request_changes(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Submit a 'request_changes' review on a conjecture returns 201."""
    author = await _create_agent(db_session, "review_author_2")
    reviewer = await _create_agent(db_session, "review_reviewer_2")

    conjecture = await _create_conjecture(client, author["headers"])

    resp = await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/reviews",
        json={"verdict": "request_changes", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["verdict"] == "request_changes"


async def test_self_review_rejected(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """Authors cannot review their own submissions."""
    author = await _create_agent(db_session, "self_review_author")

    conjecture = await _create_conjecture(client, author["headers"])

    resp = await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=author["headers"],
    )
    assert resp.status_code == 400
    assert "own submission" in resp.json()["error"].lower()


async def test_review_on_approved_rejected(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Reviews on non-pending items are rejected."""
    # Create admin agent whose submissions are auto-approved
    admin = await _create_agent(db_session, "polyproof_admin")
    reviewer = await _create_agent(db_session, "review_on_approved_reviewer")

    conjecture = await _create_conjecture(client, admin["headers"])
    assert conjecture["review_status"] == "approved"

    resp = await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 400
    assert "not pending review" in resp.json()["error"].lower()


async def test_threshold_auto_approve(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """When 3 reviewers all approve, conjecture auto-transitions to approved."""
    author = await _create_agent(db_session, "threshold_author")
    r1 = await _create_agent(db_session, "threshold_r1")
    r2 = await _create_agent(db_session, "threshold_r2")
    r3 = await _create_agent(db_session, "threshold_r3")

    conjecture = await _create_conjecture(client, author["headers"])
    cid = conjecture["id"]

    # Submit 3 approvals
    for reviewer in [r1, r2, r3]:
        resp = await client.post(
            f"/api/v1/conjectures/{cid}/reviews",
            json={"verdict": "approve", "comment": LONG_COMMENT},
            headers=reviewer["headers"],
        )
        assert resp.status_code == 201

    # Conjecture should now be approved
    detail = await client.get(f"/api/v1/conjectures/{cid}")
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "approved"


async def test_threshold_not_met_with_two_reviews(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Two approvals are not enough to meet the threshold (minimum 3)."""
    author = await _create_agent(db_session, "two_review_author")
    r1 = await _create_agent(db_session, "two_r1")
    r2 = await _create_agent(db_session, "two_r2")

    conjecture = await _create_conjecture(client, author["headers"])
    cid = conjecture["id"]

    for reviewer in [r1, r2]:
        resp = await client.post(
            f"/api/v1/conjectures/{cid}/reviews",
            json={"verdict": "approve", "comment": LONG_COMMENT},
            headers=reviewer["headers"],
        )
        assert resp.status_code == 201

    detail = await client.get(f"/api/v1/conjectures/{cid}", headers=author["headers"])
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "pending_review"


async def test_revise_conjecture(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """Author can revise a pending conjecture; version increments."""
    author = await _create_agent(db_session, "revise_author")

    conjecture = await _create_conjecture(client, author["headers"])
    assert conjecture["version"] == 1

    resp = await client.patch(
        f"/api/v1/conjectures/{conjecture['id']}",
        json={"description": "Revised description for the conjecture"},
        headers=author["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 2
    assert data["description"] == "Revised description for the conjecture"


async def test_revise_non_author_forbidden(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Non-authors cannot revise a submission."""
    author = await _create_agent(db_session, "revise_author_2")
    other = await _create_agent(db_session, "revise_other")

    conjecture = await _create_conjecture(client, author["headers"])

    resp = await client.patch(
        f"/api/v1/conjectures/{conjecture['id']}",
        json={"description": "Unauthorized revision attempt here"},
        headers=other["headers"],
    )
    assert resp.status_code == 403


async def test_reviews_on_old_version_dont_count(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """After revision, old version reviews don't count toward threshold."""
    author = await _create_agent(db_session, "version_author")
    r1 = await _create_agent(db_session, "version_r1")
    r2 = await _create_agent(db_session, "version_r2")
    r3 = await _create_agent(db_session, "version_r3")

    conjecture = await _create_conjecture(client, author["headers"])
    cid = conjecture["id"]

    # Two approvals on v1
    for reviewer in [r1, r2]:
        resp = await client.post(
            f"/api/v1/conjectures/{cid}/reviews",
            json={"verdict": "approve", "comment": LONG_COMMENT},
            headers=reviewer["headers"],
        )
        assert resp.status_code == 201

    # Revise to v2
    resp = await client.patch(
        f"/api/v1/conjectures/{cid}",
        json={"description": "Revised to version 2 with more detail"},
        headers=author["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    # One approval on v2 — should NOT meet threshold (only 1/3)
    resp = await client.post(
        f"/api/v1/conjectures/{cid}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=r3["headers"],
    )
    assert resp.status_code == 201

    detail = await client.get(f"/api/v1/conjectures/{cid}", headers=author["headers"])
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "pending_review"


async def test_list_reviews(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """GET reviews returns all reviews across versions."""
    author = await _create_agent(db_session, "list_review_author")
    reviewer = await _create_agent(db_session, "list_review_r1")

    conjecture = await _create_conjecture(client, author["headers"])
    cid = conjecture["id"]

    await client.post(
        f"/api/v1/conjectures/{cid}/reviews",
        json={"verdict": "request_changes", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )

    resp = await client.get(f"/api/v1/conjectures/{cid}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["reviews"]) == 1


async def test_duplicate_review_rejected(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Same reviewer cannot review the same version twice."""
    author = await _create_agent(db_session, "dup_review_author")
    reviewer = await _create_agent(db_session, "dup_review_r1")

    conjecture = await _create_conjecture(client, author["headers"])
    cid = conjecture["id"]

    resp = await client.post(
        f"/api/v1/conjectures/{cid}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/v1/conjectures/{cid}/reviews",
        json={"verdict": "request_changes", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 400
    assert "already reviewed" in resp.json()["error"].lower()


async def test_admin_auto_approved(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """polyproof_admin submissions are auto-approved."""
    admin = await _create_agent(db_session, "polyproof_admin")

    conjecture = await _create_conjecture(client, admin["headers"])
    assert conjecture["review_status"] == "approved"

    problem = await _create_problem(client, admin["headers"])
    assert problem["review_status"] == "approved"


async def test_default_list_shows_only_approved(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Default conjecture listing shows only approved items."""
    admin = await _create_agent(db_session, "polyproof_admin")
    regular = await _create_agent(db_session, "regular_for_list")

    # Create one approved (admin) and one pending (regular)
    await _create_conjecture(client, admin["headers"], desc="Admin conjecture approved")
    await _create_conjecture(client, regular["headers"], desc="Regular pending conjecture")

    resp = await client.get("/api/v1/conjectures")
    assert resp.status_code == 200
    for c in resp.json()["conjectures"]:
        assert c["review_status"] == "approved"


async def test_pending_review_excludes_own(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Requesting pending_review conjectures excludes your own submissions."""
    author = await _create_agent(db_session, "pending_author")

    await _create_conjecture(client, author["headers"])

    resp = await client.get(
        "/api/v1/conjectures",
        params={"review_status": "pending_review"},
        headers=author["headers"],
    )
    assert resp.status_code == 200
    # Author should not see their own pending conjecture
    for c in resp.json()["conjectures"]:
        assert c["author"]["name"] != "pending_author"


async def test_review_reputation_awarded(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Reviewer gets 3 reputation points per review."""
    author = await _create_agent(db_session, "rep_author")
    reviewer = await _create_agent(db_session, "rep_reviewer")

    conjecture = await _create_conjecture(client, author["headers"])

    me_before = (await client.get("/api/v1/agents/me", headers=reviewer["headers"])).json()

    await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/reviews",
        json={"verdict": "approve", "comment": LONG_COMMENT},
        headers=reviewer["headers"],
    )

    me_after = (await client.get("/api/v1/agents/me", headers=reviewer["headers"])).json()
    assert me_after["reputation"] == me_before["reputation"] + 3


async def test_problem_review_flow(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """Problems go through the same review flow as conjectures."""
    author = await _create_agent(db_session, "prob_review_author")
    r1 = await _create_agent(db_session, "prob_r1")
    r2 = await _create_agent(db_session, "prob_r2")
    r3 = await _create_agent(db_session, "prob_r3")

    problem = await _create_problem(client, author["headers"])
    assert problem["review_status"] == "pending_review"
    pid = problem["id"]

    # Submit 3 approvals
    for reviewer in [r1, r2, r3]:
        resp = await client.post(
            f"/api/v1/problems/{pid}/reviews",
            json={"verdict": "approve", "comment": LONG_COMMENT},
            headers=reviewer["headers"],
        )
        assert resp.status_code == 201

    detail = await client.get(f"/api/v1/problems/{pid}")
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "approved"


async def test_revise_problem(client: AsyncClient, db_session: AsyncSession, mock_lean_pass):
    """Author can revise a pending problem."""
    author = await _create_agent(db_session, "prob_revise_author")

    problem = await _create_problem(client, author["headers"])
    assert problem["version"] == 1

    resp = await client.patch(
        f"/api/v1/problems/{problem['id']}",
        json={"description": "Revised problem description with more details"},
        headers=author["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


async def test_proof_on_pending_conjecture_rejected(
    client: AsyncClient, db_session: AsyncSession, mock_lean_pass
):
    """Cannot submit proof on a conjecture that is still pending review."""
    author = await _create_agent(db_session, "proof_pending_author")
    prover = await _create_agent(db_session, "proof_pending_prover")

    conjecture = await _create_conjecture(client, author["headers"])
    assert conjecture["review_status"] == "pending_review"

    resp = await client.post(
        f"/api/v1/conjectures/{conjecture['id']}/proofs",
        json={"lean_proof": "exact trivial", "description": "simple proof"},
        headers=prover["headers"],
    )
    assert resp.status_code == 400
    assert "approved" in resp.json()["error"].lower()
