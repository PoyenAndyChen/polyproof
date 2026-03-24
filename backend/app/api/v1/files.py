"""File content endpoint."""

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.api.deps import DbSession
from app.api.rate_limit import ip_limiter
from app.errors import NotFoundError
from app.services import file_service

router = APIRouter()


@router.get("/{file_id}/content", response_class=PlainTextResponse)
@ip_limiter.limit("100/minute")
async def get_file_content(
    request: Request,
    file_id: UUID,
    db: DbSession,
) -> PlainTextResponse:
    """Serve current file content from workspace."""
    content = await file_service.get_content(db, file_id)
    if content is None:
        raise NotFoundError("File")
    return PlainTextResponse(content)
