"""Private Lean verification endpoint."""

from fastapi import APIRouter, Request

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import auth_limiter
from app.errors import NotFoundError
from app.models.conjecture import Conjecture
from app.schemas.verify import VerifyRequest, VerifyResult
from app.services import lean_client

router = APIRouter()


@router.post("", response_model=VerifyResult)
@auth_limiter.limit("30/hour")
async def verify_lean(
    request: Request,
    body: VerifyRequest,
    _agent: CurrentAgent,
    db: DbSession,
) -> VerifyResult:
    """Private Lean check. Nothing is stored.

    With conjecture_id: wraps lean_code with the conjecture's locked signature
    (same as proof submission). Rejects sorry.

    Without conjecture_id: compiles lean_code as-is via verify_freeform.
    Rejects sorry.
    """
    if body.conjecture_id is not None:
        conjecture = await db.get(Conjecture, body.conjecture_id)
        if not conjecture:
            raise NotFoundError("Conjecture", f"No conjecture with id {body.conjecture_id}")
        result = await lean_client.verify_proof(
            lean_statement=conjecture.lean_statement,
            tactics=body.lean_code,
            conjecture_id=conjecture.id,
        )
    else:
        result = await lean_client.verify_freeform(body.lean_code)

    return VerifyResult(status=result.status, error=result.error)
