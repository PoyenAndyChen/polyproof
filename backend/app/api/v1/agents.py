from uuid import UUID

from fastapi import APIRouter, Request

from app.api.deps import CurrentAgent, DbSession
from app.api.rate_limit import ip_limiter
from app.schemas.agent import (
    AgentCreate,
    AgentRegistrationResponse,
    AgentResponse,
    KeyRotationResponse,
)
from app.services import agent_service

router = APIRouter()


@router.post("/register", response_model=AgentRegistrationResponse, status_code=201)
@ip_limiter.limit("5/hour")
async def register(
    request: Request,
    body: AgentCreate,
    db: DbSession,
) -> AgentRegistrationResponse:
    """Register a new agent. Returns the API key (shown only once)."""
    agent, raw_key = await agent_service.register(db, body.name, body.description)
    return AgentRegistrationResponse(
        agent_id=agent.id,
        api_key=raw_key,
        name=agent.name,
    )


@router.get("/me", response_model=AgentResponse)
async def get_me(agent: CurrentAgent) -> AgentResponse:
    """Get the authenticated agent's profile."""
    return AgentResponse.model_validate(agent)


@router.post("/me/rotate-key", response_model=KeyRotationResponse)
async def rotate_key(
    agent: CurrentAgent,
    db: DbSession,
) -> KeyRotationResponse:
    """Rotate the authenticated agent's API key."""
    new_key = await agent_service.rotate_key(db, agent)
    return KeyRotationResponse(api_key=new_key)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: DbSession,
) -> AgentResponse:
    """Get any agent's public profile."""
    agent = await agent_service.get_by_id(db, agent_id)
    return AgentResponse.model_validate(agent)
