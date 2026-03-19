import hashlib
import secrets
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.agent import Agent


def generate_api_key() -> tuple[str, str]:
    """Generate an API key and its SHA-256 hash.

    Returns (raw_key, key_hash). The raw key is shown once to the user.
    """
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


async def register(db: AsyncSession, name: str, description: str) -> tuple[Agent, str]:
    """Register a new agent. Returns (agent, raw_api_key)."""
    existing = await db.scalar(select(Agent).where(Agent.name == name))
    if existing:
        raise ConflictError("Name already taken", f"An agent named '{name}' already exists")

    raw_key, key_hash = generate_api_key()

    agent = Agent(
        name=name,
        description=description or None,
        api_key_hash=key_hash,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent, raw_key


async def get_by_id(db: AsyncSession, agent_id: UUID) -> Agent:
    """Get an agent by ID."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise NotFoundError("Agent", f"No agent with id {agent_id}")
    return agent


async def rotate_key(db: AsyncSession, agent: Agent) -> str:
    """Generate a new API key for an agent, invalidating the old one.

    Returns the new raw API key.
    """
    raw_key, key_hash = generate_api_key()
    await db.execute(update(Agent).where(Agent.id == agent.id).values(api_key_hash=key_hash))
    await db.commit()
    return raw_key
