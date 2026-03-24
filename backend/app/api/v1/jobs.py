"""Job status endpoint."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.api.deps import DbSession
from app.api.rate_limit import ip_limiter
from app.errors import NotFoundError
from app.schemas.job import JobResponse
from app.services import job_service

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
@ip_limiter.limit("600/minute")
async def get_job(
    request: Request,
    job_id: UUID,
    db: DbSession,
) -> JobResponse:
    """Get job status. Includes lean_output on failure, new_sorries on decomposition."""
    job = await job_service.get_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job")
    return JobResponse.model_validate(job)
