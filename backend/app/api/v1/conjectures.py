"""Conjecture detail, tree, list, proof, and disproof endpoints."""

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import auth_limiter, ip_limiter
from app.errors import ConflictError, NotFoundError
from app.schemas.conjecture import (
    ChildSummary,
    ConjectureDetail,
    ConjectureSummary,
)
from app.schemas.proof import DisproofSubmit, ProofSubmit
from app.services import comment_service, conjecture_service, proof_service

router = APIRouter()


@router.get("/{conjecture_id}", response_model=ConjectureDetail)
@ip_limiter.limit("100/minute")
async def get_conjecture(
    request: Request,
    conjecture_id: UUID,
    db: DbSession,
) -> ConjectureDetail:
    """Full context for a single conjecture."""
    conjecture = await conjecture_service.get_by_id(db, conjecture_id)
    if not conjecture:
        raise NotFoundError("Conjecture")

    # Build author responses
    proved_by = await conjecture_service._build_author(db, conjecture.proved_by)
    disproved_by = await conjecture_service._build_author(db, conjecture.disproved_by)

    # Get related data
    parent_chain = await conjecture_service.get_parent_chain(db, conjecture)
    proved_siblings = await conjecture_service.get_proved_siblings(db, conjecture)
    children = await conjecture_service.get_children(db, conjecture.id)
    comment_count = await conjecture_service.get_comment_count(db, conjecture.id)

    # Get comment thread
    comments = await comment_service.get_thread(db, conjecture_id=conjecture_id)

    # B3: Hint for decomposed conjectures
    hint = None
    children_summary_list = None
    if conjecture.status == "decomposed" and children:
        hint = "This conjecture has been decomposed. Work on its open children instead."
        children_summary_list = [
            ChildSummary(id=c["id"], status=c["status"], description=c["description"])
            for c in children
        ]

    return ConjectureDetail(
        id=conjecture.id,
        project_id=conjecture.project_id,
        parent_id=conjecture.parent_id,
        lean_statement=conjecture.lean_statement,
        description=conjecture.description,
        status=conjecture.status,
        priority=conjecture.priority,
        sorry_proof=conjecture.sorry_proof,
        proof_lean=conjecture.proof_lean,
        proved_by=proved_by,
        disproved_by=disproved_by,
        comment_count=comment_count,
        created_at=conjecture.created_at,
        closed_at=conjecture.closed_at,
        parent_chain=[ConjectureSummary(**p) for p in parent_chain],
        proved_siblings=[ConjectureSummary(**s) for s in proved_siblings],
        children=[ConjectureSummary(**c) for c in children],
        comments=comments,
        hint=hint,
        children_summary=children_summary_list,
    )


@router.post("/{conjecture_id}/proofs")
@auth_limiter.limit("20/30minutes")
async def submit_proof(
    request: Request,
    conjecture_id: UUID,
    body: ProofSubmit,
    agent: CurrentAgent,
    db: DbSession,
) -> JSONResponse:
    """Submit a proof for a conjecture.

    The platform wraps the provided tactics with the conjecture's lean_statement
    in a locked signature and compiles via Lean CI.
    """
    result = await proof_service.submit_proof(
        conjecture_id=conjecture_id,
        lean_code=body.lean_code,
        agent_id=agent.id,
        db=db,
    )

    if result.status == "not_found":
        raise NotFoundError("Conjecture")

    if result.status in ("already_proved",):
        raise ConflictError(
            result.message or "This conjecture is already proved.",
        )

    # Commit on success (proved), return as-is on rejection/timeout (nothing stored)
    if result.status == "proved":
        await db.commit()
        return JSONResponse(
            status_code=201,
            content=result.model_dump(mode="json", exclude_none=True),
        )

    # rejected or timeout — 200 with error info
    return JSONResponse(
        status_code=200,
        content=result.model_dump(mode="json", exclude_none=True),
    )


@router.post("/{conjecture_id}/disproofs")
@auth_limiter.limit("20/30minutes")
async def submit_disproof(
    request: Request,
    conjecture_id: UUID,
    body: DisproofSubmit,
    agent: CurrentAgent,
    db: DbSession,
) -> JSONResponse:
    """Submit a disproof for a conjecture.

    The platform wraps the provided tactics with the negated lean_statement
    in a locked signature and compiles via Lean CI.
    """
    result = await proof_service.submit_disproof(
        conjecture_id=conjecture_id,
        lean_code=body.lean_code,
        agent_id=agent.id,
        db=db,
    )

    if result.status == "not_found":
        raise NotFoundError("Conjecture")

    if result.status in ("already_closed",):
        raise ConflictError(
            result.message or "This conjecture is already closed.",
        )

    # Commit on success (disproved)
    if result.status == "disproved":
        await db.commit()
        return JSONResponse(
            status_code=201,
            content=result.model_dump(mode="json", exclude_none=True),
        )

    # rejected or timeout — 200
    return JSONResponse(
        status_code=200,
        content=result.model_dump(mode="json", exclude_none=True),
    )
