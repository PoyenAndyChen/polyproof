"""Sorry detail and fill submission endpoints."""

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import auth_limiter, ip_limiter
from app.errors import ConflictError, NotFoundError
from app.schemas.sorry import FillRequest, FillResponse
from app.services import fill_service, sorry_service

router = APIRouter()


@router.get("/{sorry_id}")
@ip_limiter.limit("100/minute")
async def get_sorry(
    request: Request,
    sorry_id: UUID,
    db: DbSession,
) -> dict:
    """Full context for a single sorry: detail, children, parent chain, comments."""
    sorry = await sorry_service.get_by_id(db, sorry_id)
    if not sorry:
        raise NotFoundError("Sorry")

    return await sorry_service.get_detail(db, sorry)


@router.post("/{sorry_id}/fill", status_code=202)
@auth_limiter.limit("10/hour")
async def submit_fill(
    request: Request,
    sorry_id: UUID,
    body: FillRequest,
    agent: CurrentAgent,
    db: DbSession,
) -> JSONResponse:
    """Submit a fill for a sorry. Returns 202 + job_id (async compilation)."""
    sorry = await sorry_service.get_by_id(db, sorry_id)
    if not sorry:
        raise NotFoundError("Sorry")

    if sorry.status not in ("open", "decomposed"):
        raise ConflictError(
            f"Sorry is already {sorry.status} and cannot accept fills.",
        )

    result = await fill_service.submit_fill(
        db,
        sorry_id=sorry.id,
        tactics=body.tactics,
        description=body.description,
        agent_id=agent.id,
    )

    if result.get("error"):
        return JSONResponse(
            status_code=400,
            content=FillResponse(status="error", error=result["error"]).model_dump(
                mode="json", exclude_none=True
            ),
        )

    return JSONResponse(
        status_code=202,
        content=FillResponse(status="queued", job_id=result["job_id"]).model_dump(
            mode="json", exclude_none=True
        ),
    )
