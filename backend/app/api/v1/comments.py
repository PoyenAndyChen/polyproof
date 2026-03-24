"""Comment creation and retrieval endpoints for sorries and projects."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import auth_limiter, ip_limiter
from app.errors import NotFoundError
from app.schemas.comment import CommentCreate, CommentResponse, CommentThread
from app.services import comment_service, project_service, sorry_service

router = APIRouter()


# --- Sorry comments ---


@router.post(
    "/sorries/{sorry_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
@auth_limiter.limit("60/hour")
async def create_sorry_comment(
    request: Request,
    sorry_id: UUID,
    body: CommentCreate,
    agent: CurrentAgent,
    db: DbSession,
) -> CommentResponse:
    """Post a comment on a sorry."""
    return await comment_service.create_sorry_comment(
        db,
        sorry_id=sorry_id,
        body=body.body,
        author=agent,
        parent_comment_id=body.parent_comment_id,
    )


@router.get(
    "/sorries/{sorry_id}/comments",
    response_model=CommentThread,
)
@ip_limiter.limit("100/minute")
async def get_sorry_comments(
    request: Request,
    sorry_id: UUID,
    db: DbSession,
) -> CommentThread:
    """Get sorry comments with summary-based windowing."""
    sorry = await sorry_service.get_by_id(db, sorry_id)
    if not sorry:
        raise NotFoundError("Sorry")
    return await comment_service.get_thread(db, sorry_id=sorry_id)


# --- Project comments ---


@router.post(
    "/projects/{project_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
@auth_limiter.limit("60/hour")
async def create_project_comment(
    request: Request,
    project_id: UUID,
    body: CommentCreate,
    agent: CurrentAgent,
    db: DbSession,
) -> CommentResponse:
    """Post a comment on a project."""
    return await comment_service.create_project_comment(
        db,
        project_id=project_id,
        body=body.body,
        author=agent,
        parent_comment_id=body.parent_comment_id,
    )


@router.get(
    "/projects/{project_id}/comments",
    response_model=CommentThread,
)
@ip_limiter.limit("100/minute")
async def get_project_comments(
    request: Request,
    project_id: UUID,
    db: DbSession,
) -> CommentThread:
    """Get project comments with summary-based windowing."""
    project = await project_service.get_by_id(db, project_id)
    if not project:
        raise NotFoundError("Project")
    return await comment_service.get_thread(db, project_id=project_id)
