"""Build the context packet for a mega agent invocation.

The context packet is a structured text document passed as the `input`
parameter to the OpenAI Responses API. It contains sorry tree state,
recent activity, summaries, and unattended sorry's.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.project import Project
from app.models.sorry import Sorry
from app.models.tracked_file import TrackedFile

logger = logging.getLogger(__name__)


async def build_context_packet(
    project_id: UUID,
    trigger: dict,
    db: AsyncSession,
) -> str:
    """Build the full context packet for a mega agent invocation.

    Sections:
    - PROJECT: title, description, upstream_repo, fork_repo, progress
    - TRIGGER: type and details
    - SORRY TREE: all non-invalid sorry's grouped by file
    - RECENT ACTIVITY: fills, decompositions, comments since last invocation
    - PROJECT SUMMARY: latest is_summary comment on the project
    - SORRY SUMMARIES: per-sorry summaries for active nodes only
    - UNATTENDED SORRIES: open sorry's with no activity in 48+ hours
    """
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    sections = []

    # --- PROJECT section ---
    progress = await _compute_progress(project_id, db)
    sections.append(
        f"PROJECT\n\n"
        f"Title: {project.title}\n"
        f"Description: {project.description}\n"
        f"Upstream repo: {project.upstream_repo}\n"
        f"Fork repo: {project.fork_repo}\n"
        f"Progress: {progress['filled']}/{progress['total']} sorry's filled "
        f"({progress['percentage']:.0f}%)"
    )

    # --- TRIGGER section ---
    trigger_type = trigger.get("trigger", "unknown")
    trigger_details = _format_trigger(trigger_type, trigger)
    sections.append(f"TRIGGER\n\n{trigger_type}: {trigger_details}")

    # --- SORRY TREE section ---
    tree_text = await _build_sorry_tree(project_id, db)
    sections.append(f"SORRY TREE\n\n{tree_text}")

    # --- RECENT ACTIVITY section ---
    last_invocation = project.last_mega_invocation
    activity_text = await _build_recent_activity(project_id, last_invocation, db)
    sections.append(f"RECENT ACTIVITY (since start of your last invocation)\n\n{activity_text}")

    # --- PROJECT SUMMARY section ---
    project_summary = await _get_project_summary(project_id, db)
    sections.append(f"PROJECT SUMMARY\n\n{project_summary}")

    # --- SORRY SUMMARIES section ---
    sorry_summaries = await _build_sorry_summaries(project_id, last_invocation, db)
    sections.append(f"SORRY SUMMARIES (active nodes only)\n\n{sorry_summaries}")

    # --- UNATTENDED SORRIES section ---
    unattended_text = await _build_unattended_sorries(project_id, db)
    sections.append(f"UNATTENDED SORRIES (open, no activity in 48+ hours)\n\n{unattended_text}")

    return "\n\n".join(sections)


async def _compute_progress(project_id: UUID, db: AsyncSession) -> dict:
    """Count total non-invalid sorry's and filled sorry's for progress display."""
    all_sorries = await db.execute(
        select(Sorry.id, Sorry.status).where(
            Sorry.project_id == project_id,
            Sorry.status != "invalid",
        )
    )
    rows = all_sorries.all()

    # Leaves are sorry's with no non-invalid children
    parent_ids_result = await db.execute(
        select(Sorry.parent_sorry_id)
        .where(
            Sorry.project_id == project_id,
            Sorry.status != "invalid",
            Sorry.parent_sorry_id.isnot(None),
        )
        .distinct()
    )
    parent_ids = {r[0] for r in parent_ids_result.all()}

    leaves = [r for r in rows if r.id not in parent_ids]
    total = len(leaves)
    filled = sum(1 for r in leaves if r.status in ("filled", "filled_externally"))
    percentage = (filled / total * 100) if total > 0 else 0

    return {"total": total, "filled": filled, "percentage": percentage}


def _format_trigger(trigger_type: str, trigger: dict) -> str:
    """Format trigger details for the context packet."""
    if trigger_type == "project_created":
        return "New project. Study the sorry's and bootstrap."
    elif trigger_type == "activity_threshold":
        count = trigger.get("activity_count", "N")
        return f"{count} interactions since your last invocation."
    elif trigger_type == "periodic_heartbeat":
        return "24 hours since last invocation. No activity threshold fired."
    elif trigger_type == "project_completed":
        return (
            "All sorry's have been filled. The project is complete. "
            "Write a final retrospective summary."
        )
    return f"Unknown trigger: {trigger_type}"


async def _build_sorry_tree(
    project_id: UUID,
    db: AsyncSession,
) -> str:
    """Build a text representation of the sorry tree grouped by file."""
    # Fetch all non-invalid sorry's with file paths
    result = await db.execute(
        select(Sorry, TrackedFile.file_path)
        .join(TrackedFile, Sorry.file_id == TrackedFile.id)
        .where(
            Sorry.project_id == project_id,
            Sorry.status != "invalid",
        )
        .order_by(TrackedFile.file_path, Sorry.declaration_name, Sorry.sorry_index)
    )
    rows = result.all()

    if not rows:
        return "(no sorry's)"

    # Gather sorry IDs for batch queries
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

    # Batch: last activity per sorry
    last_activities: dict[UUID, datetime] = {}
    if sorry_ids:
        la_result = await db.execute(
            select(ActivityLog.sorry_id, func.max(ActivityLog.created_at))
            .where(ActivityLog.sorry_id.in_(sorry_ids))
            .group_by(ActivityLog.sorry_id)
        )
        last_activities = dict(la_result.all())

    # Batch: filled_by agent handles
    filled_by_ids = {row[0].filled_by for row in rows if row[0].filled_by is not None}
    agent_handles: dict[UUID, str] = {}
    if filled_by_ids:
        agents_result = await db.execute(
            select(Agent.id, Agent.handle).where(Agent.id.in_(filled_by_ids))
        )
        agent_handles = dict(agents_result.all())

    # Group by file
    files: dict[str, list] = {}
    for sorry, file_path in rows:
        if file_path not in files:
            files[file_path] = []
        files[file_path].append(sorry)

    lines = []
    for file_path, sorries in files.items():
        lines.append(f"FILE: {file_path}")
        lines.append("")

        for sorry in sorries:
            # Truncate goal_state
            goal_preview = sorry.goal_state[:150].replace("\n", " ")
            status = sorry.status
            priority = sorry.priority

            # Last activity
            last_act = last_activities.get(sorry.id)
            if last_act:
                days_ago = (datetime.now(UTC) - last_act).total_seconds() / 86400
                activity_str = f"{days_ago:.1f}d ago"
            else:
                activity_str = "never"

            cc = comment_counts.get(sorry.id, 0)

            line = (
                f"  {sorry.id} | {sorry.declaration_name}[{sorry.sorry_index}] "
                f"| {status} | priority:{priority}"
            )
            lines.append(line)
            lines.append(f"    Goal: {goal_preview}")
            lines.append(
                f"    Active agents: {sorry.active_agents} | "
                f"Comments: {cc} | Last activity: {activity_str}"
            )

            if status in ("filled", "filled_externally") and sorry.filled_by:
                handle = agent_handles.get(sorry.filled_by, "unknown")
                tactics_preview = (sorry.fill_tactics or "")[:200]
                lines.append(f"    Filled by: {handle} | Tactics: {tactics_preview}")

            if status == "decomposed":
                # Count children
                child_count_result = await db.scalar(
                    select(func.count()).where(
                        Sorry.parent_sorry_id == sorry.id,
                        Sorry.status != "invalid",
                    )
                )
                lines.append(f"    Children: {child_count_result or 0}")

            if sorry.parent_sorry_id:
                lines.append(f"    Parent: {sorry.parent_sorry_id}")

            lines.append("")

    return "\n".join(lines)


async def _build_recent_activity(
    project_id: UUID,
    last_invocation: datetime | None,
    db: AsyncSession,
) -> str:
    """Build the RECENT ACTIVITY section from activity_log."""
    if last_invocation is None:
        return "(no prior invocation)"

    stmt = (
        select(ActivityLog, Agent.handle.label("agent_handle"))
        .outerjoin(Agent, ActivityLog.agent_id == Agent.id)
        .where(
            ActivityLog.project_id == project_id,
            ActivityLog.created_at > last_invocation,
        )
        .order_by(ActivityLog.created_at)
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return "(no activity since last invocation)"

    sections: dict[str, list[str]] = {
        "Comments": [],
        "Fills": [],
        "Decompositions": [],
        "Priority changes": [],
    }

    for row in rows:
        event = row[0]
        handle = row.agent_handle or "system"
        details = event.details or {}
        time_str = event.created_at.strftime("%Y-%m-%d %H:%M UTC")
        sorry_id = str(event.sorry_id) if event.sorry_id else "project"

        if event.event_type == "comment":
            body_preview = details.get("body_preview", "")[:500]
            sections["Comments"].append(f"  {time_str} | {handle} on {sorry_id}:\n  {body_preview}")
        elif event.event_type == "fill":
            job_status = details.get("status", "")
            sections["Fills"].append(
                f"  {time_str} | {handle} submitted fill for {sorry_id} (status: {job_status})"
            )
        elif event.event_type == "decomposition":
            sections["Decompositions"].append(
                f"  {time_str} | decomposition on {sorry_id} by {handle}"
            )
        elif event.event_type == "priority_changed":
            old_p = details.get("old_priority", "?")
            new_p = details.get("new_priority", "?")
            sections["Priority changes"].append(
                f"  {time_str} | {sorry_id} priority: {old_p} -> {new_p}"
            )

    parts = []
    for section_name, entries in sections.items():
        if entries:
            parts.append(f"{section_name}:\n" + "\n".join(entries))

    return "\n\n".join(parts) if parts else "(no activity since last invocation)"


async def _get_project_summary(project_id: UUID, db: AsyncSession) -> str:
    """Get the latest is_summary comment on the project."""
    stmt = (
        select(Comment.body)
        .where(
            Comment.project_id == project_id,
            Comment.is_summary.is_(True),
        )
        .order_by(Comment.created_at.desc())
        .limit(1)
    )
    summary = await db.scalar(stmt)
    return summary if summary else "(no summary yet)"


async def _build_sorry_summaries(
    project_id: UUID,
    last_invocation: datetime | None,
    db: AsyncSession,
) -> str:
    """Build per-sorry summaries for active nodes."""
    # Get active sorry's (open or decomposed)
    active_sorries = await db.execute(
        select(
            Sorry.id, Sorry.declaration_name, Sorry.sorry_index, Sorry.goal_state, Sorry.status
        ).where(
            Sorry.project_id == project_id,
            Sorry.status.in_(["open", "decomposed"]),
        )
    )
    sorries = active_sorries.all()

    if not sorries:
        return "(no active sorry's)"

    parts = []
    for sorry in sorries:
        sorry_id = sorry.id
        goal_preview = sorry.goal_state[:100].replace("\n", " ")

        # Get latest summary
        summary_stmt = (
            select(Comment.body, Comment.created_at)
            .where(
                Comment.sorry_id == sorry_id,
                Comment.is_summary.is_(True),
            )
            .order_by(Comment.created_at.desc())
            .limit(1)
        )
        summary_row = (await db.execute(summary_stmt)).first()
        summary_text = summary_row[0] if summary_row else "(no summary)"
        summary_time = summary_row[1] if summary_row else None

        # Get comments since summary (or since last invocation)
        cutoff = summary_time or last_invocation
        comments_after = []
        if cutoff:
            comments_stmt = (
                select(Comment.body, Comment.created_at, Agent.handle)
                .join(Agent, Agent.id == Comment.author_id)
                .where(
                    Comment.sorry_id == sorry_id,
                    Comment.created_at > cutoff,
                    Comment.is_summary.is_(False),
                )
                .order_by(Comment.created_at)
            )
            rows = (await db.execute(comments_stmt)).all()
            for row in rows:
                time_str = row[1].strftime("%Y-%m-%d %H:%M UTC")
                body_preview = row[0][:300]
                comments_after.append(f"  {time_str} | {row[2]}: {body_preview}")

        entry = (
            f"Sorry {sorry_id} -- {sorry.declaration_name}[{sorry.sorry_index}]\n"
            f"Goal: {goal_preview}\n"
        )
        entry += f"Summary: {summary_text}\n"
        if comments_after:
            entry += "Comments since summary:\n" + "\n".join(comments_after)
        else:
            entry += "Comments since summary: (none)"

        parts.append(entry)

    return "\n\n".join(parts)


async def _build_unattended_sorries(project_id: UUID, db: AsyncSession) -> str:
    """Find open sorry's with no activity in 48+ hours."""
    threshold = datetime.now(UTC) - timedelta(hours=48)

    # Open sorry's
    open_stmt = select(Sorry.id, Sorry.declaration_name, Sorry.sorry_index, Sorry.goal_state).where(
        Sorry.project_id == project_id,
        Sorry.status == "open",
    )
    sorries = (await db.execute(open_stmt)).all()

    unattended_entries = []
    for sorry in sorries:
        # Check for recent activity
        recent_activity = await db.scalar(
            select(func.count()).where(
                ActivityLog.sorry_id == sorry.id,
                ActivityLog.created_at > threshold,
            )
        )
        recent_comments = await db.scalar(
            select(func.count()).where(
                Comment.sorry_id == sorry.id,
                Comment.created_at > threshold,
            )
        )

        if (recent_activity or 0) == 0 and (recent_comments or 0) == 0:
            comment_count = await db.scalar(
                select(func.count()).where(Comment.sorry_id == sorry.id)
            )
            goal_preview = sorry.goal_state[:120].replace("\n", " ")

            entry = (
                f"{sorry.id} | {sorry.declaration_name}[{sorry.sorry_index}] "
                f'| "{goal_preview}" | {comment_count or 0} comments'
            )

            # Get last few comments for context
            last_comments = (
                await db.execute(
                    select(Comment.body, Comment.created_at, Agent.handle)
                    .join(Agent, Agent.id == Comment.author_id)
                    .where(Comment.sorry_id == sorry.id)
                    .order_by(Comment.created_at.desc())
                    .limit(3)
                )
            ).all()

            if last_comments:
                entry += "\nLast comments:"
                for c in reversed(last_comments):
                    time_str = c[1].strftime("%Y-%m-%d %H:%M UTC")
                    body_preview = c[0][:200]
                    entry += f"\n  {time_str} | {c[2]}: {body_preview}"

            unattended_entries.append(entry)

    return "\n\n".join(unattended_entries) if unattended_entries else "(no unattended sorry's)"
