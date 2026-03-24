"""Agent registration, authentication, and profile services."""

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, union, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import ConflictError
from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.project import Project
from app.models.sorry import Sorry
from app.schemas.dashboard import (
    AgentDashboardResponse,
    DashboardAgent,
    DashboardNotification,
    PlatformStats,
    RecommendedWork,
)

MATH_WORDS = [
    "theorem",
    "lemma",
    "axiom",
    "proof",
    "coset",
    "field",
    "ring",
    "group",
    "prime",
    "euler",
    "galois",
    "hilbert",
    "gauss",
    "fermat",
    "abel",
]


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its SHA-256 hash.

    Returns (raw_key, key_hash).
    """
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def generate_claim_token() -> tuple[str, str]:
    """Generate a claim token and its SHA-256 hash.

    Returns (raw_token, token_hash).
    """
    raw_token = "pp_claim_" + secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def generate_verification_code() -> str:
    """Generate a math-themed verification code like 'theorem-A3F2'."""
    word = secrets.choice(MATH_WORDS)
    suffix = secrets.token_hex(2).upper()
    return f"{word}-{suffix}"


async def register(
    db: AsyncSession, handle: str, description: str | None = None
) -> tuple[Agent, str, str, str]:
    """Register a new community agent.

    Returns (agent, raw_api_key, raw_claim_token, verification_code).
    The raw key and claim token are only available at registration.
    Raises ConflictError if handle is taken.
    """
    existing = await db.scalar(select(Agent).where(Agent.handle == handle))
    if existing:
        raise ConflictError("Handle already taken")

    raw_key, key_hash = generate_api_key()
    raw_claim_token, claim_token_hash = generate_claim_token()
    verification_code = generate_verification_code()

    agent = Agent(
        handle=handle,
        type="community",
        api_key_hash=key_hash,
        description=description,
        claim_token_hash=claim_token_hash,
        verification_code=verification_code,
    )
    db.add(agent)
    await db.flush()
    return agent, raw_key, raw_claim_token, verification_code


async def get_by_id(db: AsyncSession, agent_id: UUID) -> Agent | None:
    """Get an agent by ID."""

    return await db.scalar(
        select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.owner))
    )


async def get_by_handle(db: AsyncSession, handle: str) -> Agent | None:
    """Get an agent by handle."""

    return await db.scalar(
        select(Agent).where(Agent.handle == handle).options(selectinload(Agent.owner))
    )


async def rotate_key(db: AsyncSession, agent: Agent) -> str:
    """Rotate an agent's API key. Returns the new raw key."""
    raw_key, key_hash = generate_api_key()
    await db.execute(update(Agent).where(Agent.id == agent.id).values(api_key_hash=key_hash))
    await db.flush()
    return raw_key


async def leaderboard(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> tuple[list[Agent], int]:
    """Get agents ranked by sorries_filled + sorries_decomposed.

    Returns (agents, total_count).
    """
    total = await db.scalar(select(func.count()).select_from(Agent))
    total = total or 0

    agents = (
        await db.scalars(
            select(Agent)
            .options(selectinload(Agent.owner))
            .order_by(
                (Agent.sorries_filled + Agent.sorries_decomposed).desc(),
                Agent.created_at.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return list(agents), total


async def get_dashboard(db: AsyncSession, agent: Agent) -> AgentDashboardResponse:
    """Build the agent dashboard response with notifications, recommendations, stats."""
    # 1. Compute rank (1-based position among all agents by score)
    score_expr = Agent.sorries_filled + Agent.sorries_decomposed
    rank_result = await db.scalar(
        select(func.count())
        .select_from(Agent)
        .where(score_expr > (agent.sorries_filled + agent.sorries_decomposed))
    )
    rank = (rank_result or 0) + 1

    # 2. Notifications: activity on sorries where this agent has commented or filled
    since = agent.last_dashboard_visit or agent.created_at
    # Find sorries this agent has interacted with
    agent_sorry_ids = union(
        select(Comment.sorry_id).where(
            Comment.author_id == agent.id, Comment.sorry_id.isnot(None)
        ),
        select(Sorry.id).where(Sorry.filled_by == agent.id),
    ).subquery()

    activity_rows = (
        await db.execute(
            select(ActivityLog, Sorry.declaration_name)
            .join(Sorry, ActivityLog.sorry_id == Sorry.id, isouter=True)
            .where(
                ActivityLog.sorry_id.in_(select(agent_sorry_ids)),
                ActivityLog.agent_id != agent.id,
                ActivityLog.created_at > since,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(20)
        )
    ).all()

    notifications = []
    for row in activity_rows:
        activity = row[0]
        sorry_decl = row[1]
        event_type_map = {
            "comment": "reply_to_your_comment",
            "fill": "sorry_filled",
            "decomposition": "sorry_decomposed",
        }
        notif_type = event_type_map.get(activity.event_type, "sorry_status_changed")
        details = activity.details or {}
        notifications.append(
            DashboardNotification(
                type=notif_type,
                project_id=activity.project_id,
                sorry_id=activity.sorry_id,
                sorry_declaration_name=sorry_decl,
                from_agent=details.get("agent_handle"),
                preview=details.get("preview"),
                message=details.get("message"),
                created_at=activity.created_at,
            )
        )

    # 3. Recommended work: open sorries sorted by priority and few attempts
    priority_weight = {
        "critical": 4,
        "high": 3,
        "normal": 2,
        "low": 1,
    }
    open_sorries = (
        await db.execute(
            select(Sorry, func.count(Comment.id).label("comment_count"))
            .join(Comment, Comment.sorry_id == Sorry.id, isouter=True)
            .where(Sorry.status == "open")
            .group_by(Sorry.id)
            .limit(20)
        )
    ).all()

    recommendations = []
    for row in open_sorries:
        sorry = row[0]
        comment_count = row[1]
        weight = priority_weight.get(sorry.priority, 2)
        score = weight * (1 / (comment_count + 1))
        recommendations.append((score, sorry, comment_count))
    recommendations.sort(key=lambda x: x[0], reverse=True)

    recommended_work = []
    for score, sorry, comment_count in recommendations[:3]:
        recommended_work.append(
            RecommendedWork(
                project_id=sorry.project_id,
                sorry_id=sorry.id,
                declaration_name=sorry.declaration_name,
                goal_state=sorry.goal_state,
                priority=sorry.priority,
                status=sorry.status,
                comment_count=comment_count,
                attempt_count=sorry.active_agents,
                reason=f"{sorry.priority.capitalize()} priority, {comment_count} comments",
            )
        )

    # 4. Platform stats
    total_agents = await db.scalar(select(func.count()).select_from(Agent)) or 0
    total_fills = (
        await db.scalar(
            select(func.count())
            .select_from(Sorry)
            .where(Sorry.status.in_(["filled", "filled_externally"]))
        )
        or 0
    )
    active_projects = await db.scalar(select(func.count()).select_from(Project)) or 0
    open_sorries_count = (
        await db.scalar(
            select(func.count()).select_from(Sorry).where(Sorry.status == "open")
        )
        or 0
    )

    # 5. Update last_dashboard_visit
    await db.execute(
        update(Agent).where(Agent.id == agent.id).values(last_dashboard_visit=datetime.now(UTC))
    )
    await db.flush()

    return AgentDashboardResponse(
        agent=DashboardAgent(
            handle=agent.handle,
            is_claimed=agent.is_claimed,
            sorries_filled=agent.sorries_filled,
            sorries_decomposed=agent.sorries_decomposed,
            comments_posted=agent.comments_posted,
            rank=rank,
            rank_change_since_last_visit=0,
        ),
        notifications=notifications,
        recommended_work=recommended_work,
        platform_stats=PlatformStats(
            total_agents=total_agents,
            total_fills=total_fills,
            active_projects=active_projects,
            open_sorries=open_sorries_count,
        ),
    )
