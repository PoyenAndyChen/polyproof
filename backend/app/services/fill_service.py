"""Fill submission — creates async jobs for sorry filling."""

import asyncio
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services import activity_service

# Track which projects have a running worker to avoid duplicates
_active_workers: set[UUID] = set()


async def submit_fill(
    db: AsyncSession,
    sorry_id: UUID,
    tactics: str,
    description: str,
    agent_id: UUID,
) -> dict:
    """Submit a fill for a sorry.

    Creates a Job with status='queued'. Does NOT compile synchronously.
    Uses SELECT FOR UPDATE to verify the sorry is still open before creating the job.

    Returns dict with status and job_id.
    """
    # Lock the sorry row to check status
    lock_result = await db.execute(
        text("SELECT id, status, project_id FROM sorries WHERE id = :id FOR UPDATE"),
        {"id": str(sorry_id)},
    )
    locked_row = lock_result.first()

    if locked_row is None:
        return {"status": "error", "error": "Sorry not found"}

    if locked_row.status not in ("open", "decomposed"):
        return {
            "status": "error",
            "error": f"Sorry is {locked_row.status} — cannot submit fill.",
        }

    project_id = locked_row.project_id

    # Create the job
    job = Job(
        project_id=project_id,
        sorry_id=sorry_id,
        agent_id=agent_id,
        job_type="fill",
        status="queued",
        tactics=tactics,
        description=description,
    )
    db.add(job)
    await db.flush()

    # Log activity
    await activity_service.record_event(
        db,
        project_id=project_id,
        event_type="fill",
        sorry_id=sorry_id,
        agent_id=agent_id,
        details={"job_id": str(job.id), "status": "queued"},
    )

    # Kick off a background worker if one isn't already running for this project
    if project_id not in _active_workers:
        _active_workers.add(project_id)

        async def _run_worker():
            try:
                from app.services.job_service import start_worker

                await start_worker(project_id)
            finally:
                _active_workers.discard(project_id)

        asyncio.create_task(_run_worker())

    return {"status": "queued", "job_id": job.id}
