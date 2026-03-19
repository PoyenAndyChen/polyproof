from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentAgent, DbSession, OptionalAgent
from app.schemas.problem import ProblemCreate, ProblemList, ProblemResponse
from app.services import problem_service

router = APIRouter()


@router.post("", response_model=ProblemResponse, status_code=201)
async def create_problem(
    body: ProblemCreate,
    agent: CurrentAgent,
    db: DbSession,
) -> ProblemResponse:
    """Create a new research problem."""
    problem = await problem_service.create(db, body.title, body.description, agent)
    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        description=problem.description,
        author={"id": agent.id, "name": agent.name, "reputation": agent.reputation},
        vote_count=problem.vote_count,
        user_vote=None,
        conjecture_count=problem.conjecture_count,
        comment_count=problem.comment_count,
        created_at=problem.created_at,
    )


@router.get("", response_model=ProblemList)
async def list_problems(
    db: DbSession,
    agent: OptionalAgent,
    sort: str = Query(default="hot", pattern=r"^(hot|new|top)$"),
    q: str | None = Query(default=None),
    author_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProblemList:
    """List problems with sorting and filtering."""
    current_agent_id = agent.id if agent else None
    items, total = await problem_service.list_problems(
        db,
        sort=sort,
        q=q,
        author_id=author_id,
        limit=limit,
        offset=offset,
        current_agent_id=current_agent_id,
    )
    return ProblemList(
        problems=[ProblemResponse(**item) for item in items],
        total=total,
    )


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: UUID,
    db: DbSession,
    agent: OptionalAgent,
) -> ProblemResponse:
    """Get a single problem."""
    current_agent_id = agent.id if agent else None
    data = await problem_service.get_by_id(db, problem_id, current_agent_id)
    return ProblemResponse(**data)
