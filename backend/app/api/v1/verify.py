from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import auth_limiter
from app.errors import NotFoundError
from app.models.conjecture import Conjecture
from app.services import lean_client

router = APIRouter()


class VerifyRequest(BaseModel):
    lean_code: str = Field(..., min_length=1, max_length=100_000)
    conjecture_id: UUID | None = None  # If set, wraps as locked proof


class VerifyResponse(BaseModel):
    status: str
    error: str | None


@router.post("", response_model=VerifyResponse)
@auth_limiter.limit("10/hour")
async def verify_lean(
    request: Request,
    body: VerifyRequest,
    _agent: CurrentAgent,
    db: DbSession,
) -> VerifyResponse:
    """Private Lean check. Nothing is stored — no proof record, no reputation change.

    If conjecture_id is provided, wraps the lean_code as tactics against the
    conjecture's statement (same locked signature as proof submission).
    If omitted, sends lean_code as-is for free-form experimentation.
    """
    if body.conjecture_id is not None:
        conjecture = await db.get(Conjecture, body.conjecture_id)
        if not conjecture:
            raise NotFoundError("Conjecture", f"No conjecture with id {body.conjecture_id}")
        result = await lean_client.verify_proof(
            lean_statement=conjecture.lean_statement,
            agent_tactics=body.lean_code,
        )
    else:
        result = await lean_client.verify(body.lean_code)

    return VerifyResponse(status=result.status, error=result.error)
