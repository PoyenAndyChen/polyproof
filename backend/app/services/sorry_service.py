"""Sorry tree queries and detail views."""

from uuid import UUID

from sqlalchemy import case, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.sorry import Sorry
from app.models.tracked_file import TrackedFile
from app.schemas.agent import AuthorResponse


async def get_by_id(db: AsyncSession, sorry_id: UUID) -> Sorry | None:
    """Get a sorry by ID."""
    return await db.get(Sorry, sorry_id)


async def _build_author(db: AsyncSession, agent_id: UUID | None) -> AuthorResponse | None:
    """Build an AuthorResponse from an agent ID."""
    if agent_id is None:
        return None
    agent = await db.get(Agent, agent_id)
    if agent is None:
        return None
    return AuthorResponse(
        id=agent.id,
        handle=agent.handle,
        type=agent.type,
        sorries_filled=agent.sorries_filled,
    )


async def get_comment_count(db: AsyncSession, sorry_id: UUID) -> int:
    """Count comments for a sorry."""
    result = await db.scalar(
        select(func.count()).select_from(Comment).where(Comment.sorry_id == sorry_id)
    )
    return result or 0


async def get_parent_chain(db: AsyncSession, sorry: Sorry) -> list[dict]:
    """Get the ancestor chain from root to immediate parent.

    Returns list ordered root-first, excluding the sorry itself.
    """
    if sorry.parent_sorry_id is None:
        return []

    query = text("""
        WITH RECURSIVE ancestors AS (
            SELECT id, parent_sorry_id, declaration_name, sorry_index,
                   goal_state, status, 0 AS depth
            FROM sorries
            WHERE id = :start_id

            UNION ALL

            SELECT s.id, s.parent_sorry_id, s.declaration_name, s.sorry_index,
                   s.goal_state, s.status, a.depth + 1
            FROM sorries s
            JOIN ancestors a ON s.id = a.parent_sorry_id
        )
        SELECT id, declaration_name, sorry_index, goal_state, status
        FROM ancestors
        WHERE id != :self_id
        ORDER BY depth DESC
    """)
    result = await db.execute(
        query, {"start_id": str(sorry.parent_sorry_id), "self_id": str(sorry.id)}
    )
    rows = result.all()
    return [
        {
            "id": row.id,
            "declaration_name": row.declaration_name,
            "sorry_index": row.sorry_index,
            "goal_state": row.goal_state,
            "status": row.status,
        }
        for row in rows
    ]


async def get_children(db: AsyncSession, sorry_id: UUID) -> list[dict]:
    """Get direct children of a sorry, excluding invalid ones."""
    result = await db.execute(
        select(Sorry)
        .where(
            Sorry.parent_sorry_id == sorry_id,
            Sorry.status != "invalid",
        )
        .order_by(Sorry.created_at.asc())
    )
    children = result.scalars().all()
    items = []
    for c in children:
        items.append(
            {
                "id": c.id,
                "declaration_name": c.declaration_name,
                "sorry_index": c.sorry_index,
                "goal_state": c.goal_state,
                "status": c.status,
                "priority": c.priority,
            }
        )
    return items


async def get_tree(db: AsyncSession, project_id: UUID) -> list[dict]:
    """Build the full sorry tree for a project as a nested structure.

    Returns a list of root-level nodes (sorries with no parent), each with
    nested children arrays.
    """
    # Fetch all non-invalid sorries for the project
    result = await db.execute(
        select(Sorry, TrackedFile.file_path)
        .join(TrackedFile, Sorry.file_id == TrackedFile.id)
        .where(Sorry.project_id == project_id)
        .order_by(Sorry.created_at.asc())
    )
    rows = result.all()

    if not rows:
        return []

    sorry_ids = [row[0].id for row in rows]

    # Batch: comment counts
    comment_counts: dict[UUID, int] = {}
    if sorry_ids:
        cc_result = await db.execute(
            select(Comment.sorry_id, func.count())
            .where(Comment.sorry_id.in_(sorry_ids))
            .group_by(Comment.sorry_id)
        )
        comment_counts = dict(cc_result.all())

    # Batch: filled_by agent handles
    filled_by_ids = {row[0].filled_by for row in rows if row[0].filled_by is not None}
    agent_handles: dict[UUID, str] = {}
    if filled_by_ids:
        agents_result = await db.execute(
            select(Agent.id, Agent.handle).where(Agent.id.in_(filled_by_ids))
        )
        agent_handles = dict(agents_result.all())

    # Build nodes keyed by id
    nodes: dict[UUID, dict] = {}
    for sorry, file_path in rows:
        nodes[sorry.id] = {
            "id": sorry.id,
            "declaration_name": sorry.declaration_name,
            "sorry_index": sorry.sorry_index,
            "goal_state": sorry.goal_state,
            "status": sorry.status,
            "priority": sorry.priority,
            "filled_by": agent_handles.get(sorry.filled_by) if sorry.filled_by else None,
            "active_agents": sorry.active_agents,
            "parent_sorry_id": sorry.parent_sorry_id,
            "comment_count": comment_counts.get(sorry.id, 0),
            "children": [],
        }

    # Build tree structure
    roots = []
    for node in nodes.values():
        parent_id = node["parent_sorry_id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


async def list_for_project(
    db: AsyncSession,
    project_id: UUID,
    status: str | None = None,
    priority: str | None = None,
    order_by: str = "priority",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List sorries for a project with filters.

    Returns (sorry_dicts, total_count).
    """
    base = select(Sorry, TrackedFile.file_path).join(
        TrackedFile, Sorry.file_id == TrackedFile.id
    ).where(Sorry.project_id == project_id)

    if status:
        base = base.where(Sorry.status == status)
    else:
        # Default: exclude invalid
        base = base.where(Sorry.status != "invalid")

    if priority:
        base = base.where(Sorry.priority == priority)

    # Count (need a subquery on just Sorry for counting)
    count_base = select(Sorry).where(Sorry.project_id == project_id)
    if status:
        count_base = count_base.where(Sorry.status == status)
    else:
        count_base = count_base.where(Sorry.status != "invalid")
    if priority:
        count_base = count_base.where(Sorry.priority == priority)
    count_q = select(func.count()).select_from(count_base.subquery())
    total = await db.scalar(count_q) or 0

    # Ordering
    if order_by == "created_at":
        base = base.order_by(Sorry.created_at.desc())
    else:
        # priority ordering: critical > high > normal > low, then created_at desc
        priority_order = case(
            (Sorry.priority == "critical", 0),
            (Sorry.priority == "high", 1),
            (Sorry.priority == "normal", 2),
            (Sorry.priority == "low", 3),
            else_=4,
        )
        base = base.order_by(priority_order.asc(), Sorry.created_at.desc())

    base = base.limit(limit).offset(offset)
    result = await db.execute(base)
    rows = result.all()

    # Batch: filled_by authors and comment counts
    sorry_ids = [row[0].id for row in rows]
    filled_by_ids = {row[0].filled_by for row in rows if row[0].filled_by is not None}

    agent_map: dict[UUID, AuthorResponse] = {}
    if filled_by_ids:
        for aid in filled_by_ids:
            author = await _build_author(db, aid)
            if author:
                agent_map[aid] = author

    comment_counts: dict[UUID, int] = {}
    if sorry_ids:
        cc_result = await db.execute(
            select(Comment.sorry_id, func.count())
            .where(Comment.sorry_id.in_(sorry_ids))
            .group_by(Comment.sorry_id)
        )
        comment_counts = dict(cc_result.all())

    items = []
    for sorry, file_path in rows:
        filled_by = agent_map.get(sorry.filled_by) if sorry.filled_by else None
        items.append(
            {
                "id": sorry.id,
                "file_id": sorry.file_id,
                "project_id": sorry.project_id,
                "declaration_name": sorry.declaration_name,
                "sorry_index": sorry.sorry_index,
                "goal_state": sorry.goal_state,
                "local_context": sorry.local_context,
                "status": sorry.status,
                "priority": sorry.priority,
                "active_agents": sorry.active_agents,
                "filled_by": filled_by,
                "fill_tactics": sorry.fill_tactics,
                "fill_description": sorry.fill_description,
                "filled_at": sorry.filled_at,
                "parent_sorry_id": sorry.parent_sorry_id,
                "file_path": file_path,
                "comment_count": comment_counts.get(sorry.id, 0),
                "line": sorry.line,
                "col": sorry.col,
                "created_at": sorry.created_at,
            }
        )

    return items, total


async def get_detail(db: AsyncSession, sorry: Sorry) -> dict:
    """Get sorry detail with children, parent chain, and comments."""
    from app.services.comment_service import get_thread

    filled_by = await _build_author(db, sorry.filled_by)
    children = await get_children(db, sorry.id)
    parent_chain = await get_parent_chain(db, sorry)
    comment_thread = await get_thread(db, sorry_id=sorry.id)
    comment_count = await get_comment_count(db, sorry.id)

    # Get file path
    tracked_file = await db.get(TrackedFile, sorry.file_id)
    file_path = tracked_file.file_path if tracked_file else ""

    return {
        "id": sorry.id,
        "file_id": sorry.file_id,
        "project_id": sorry.project_id,
        "declaration_name": sorry.declaration_name,
        "sorry_index": sorry.sorry_index,
        "goal_state": sorry.goal_state,
        "local_context": sorry.local_context,
        "status": sorry.status,
        "priority": sorry.priority,
        "active_agents": sorry.active_agents,
        "filled_by": filled_by,
        "fill_tactics": sorry.fill_tactics,
        "fill_description": sorry.fill_description,
        "filled_at": sorry.filled_at,
        "parent_sorry_id": sorry.parent_sorry_id,
        "file_path": file_path,
        "comment_count": comment_count,
        "line": sorry.line,
        "col": sorry.col,
        "created_at": sorry.created_at,
        "children": children,
        "parent_chain": parent_chain,
        "comments": comment_thread,
    }


async def set_priority(
    sorry_id: UUID,
    priority: str,
    mega_agent_id: UUID,
    project_id: UUID,
    db: AsyncSession,
) -> dict:
    """Set a sorry's priority level. Called by the mega agent."""
    from uuid import uuid4 as _uuid4

    valid_priorities = {"critical", "high", "normal", "low"}
    if priority not in valid_priorities:
        return {"status": "error", "error": f"Invalid priority: {priority}"}

    sorry = await db.get(Sorry, sorry_id)
    if not sorry:
        return {"status": "error", "error": f"Sorry {sorry_id} not found."}

    old_priority = sorry.priority

    await db.execute(
        update(Sorry).where(Sorry.id == sorry_id).values(priority=priority)
    )

    activity = ActivityLog(
        id=_uuid4(),
        project_id=project_id,
        event_type="priority_changed",
        sorry_id=sorry_id,
        agent_id=mega_agent_id,
        details={"old_priority": old_priority, "new_priority": priority},
    )
    db.add(activity)
    await db.flush()

    return {
        "status": "ok",
        "sorry_id": str(sorry_id),
        "priority": priority,
    }
