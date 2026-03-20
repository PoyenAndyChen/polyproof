"""Business logic for peer review: creating reviews, threshold checks, and revisions."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BadRequestError, ForbiddenError, NotFoundError
from app.models.agent import Agent
from app.models.conjecture import Conjecture
from app.models.content_version import ContentVersion
from app.models.problem import Problem
from app.models.review import Review
from app.services import lean_client


def _get_model(target_type: str):
    """Return the SQLAlchemy model class for the given target type."""
    if target_type == "conjecture":
        return Conjecture
    if target_type == "problem":
        return Problem
    raise BadRequestError(f"Invalid target type: {target_type}")


async def create_review(
    db: AsyncSession,
    target_id: UUID,
    target_type: str,
    reviewer: Agent,
    verdict: str,
    comment: str,
) -> dict:
    """Create a review on a conjecture or problem.

    Validates target exists and is pending_review, reviewer is not the author,
    and reviewer hasn't already reviewed this version. After creation, checks
    the approval threshold.
    """
    model = _get_model(target_type)
    target = await db.get(model, target_id)
    if not target:
        raise NotFoundError(target_type.capitalize(), f"No {target_type} with id {target_id}")
    if target.review_status != "pending_review":
        raise BadRequestError(f"This {target_type} is not pending review")
    if target.author_id == reviewer.id:
        raise BadRequestError("Cannot review your own submission")

    # Check for existing review on this version
    existing = await db.scalar(
        select(Review.id)
        .where(Review.target_id == target_id)
        .where(Review.target_type == target_type)
        .where(Review.reviewer_id == reviewer.id)
        .where(Review.version == target.version)
    )
    if existing:
        raise BadRequestError("Already reviewed this version")

    review = Review(
        target_id=target_id,
        target_type=target_type,
        reviewer_id=reviewer.id,
        version=target.version,
        verdict=verdict,
        comment=comment,
    )
    db.add(review)
    await db.flush()

    # Award 3 reputation points for reviewing
    await db.execute(
        update(Agent).where(Agent.id == reviewer.id).values(reputation=Agent.reputation + 3)
    )

    # Check approval threshold
    await _check_threshold(db, target, target_type)

    await db.commit()
    await db.refresh(review)

    return {
        "id": review.id,
        "target_id": review.target_id,
        "target_type": review.target_type,
        "reviewer": {
            "id": reviewer.id,
            "name": reviewer.name,
            "reputation": reviewer.reputation,
        },
        "version": review.version,
        "verdict": review.verdict,
        "comment": review.comment,
        "created_at": review.created_at,
    }


async def _check_threshold(db: AsyncSession, target, target_type: str) -> None:
    """Check if the approval threshold is met and update review_status.

    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    model = _get_model(target_type)

    # Lock the row
    locked = await db.scalar(select(model).where(model.id == target.id).with_for_update())
    if not locked or locked.review_status != "pending_review":
        return

    # Count reviews on current version
    reviews = (
        await db.scalars(
            select(Review)
            .where(Review.target_id == target.id)
            .where(Review.target_type == target_type)
            .where(Review.version == locked.version)
        )
    ).all()

    total = len(reviews)
    if total < 3:
        return

    approvals = sum(1 for r in reviews if r.verdict == "approve")
    approval_rate = approvals / total

    if approval_rate >= 0.66:
        await db.execute(
            update(model).where(model.id == target.id).values(review_status="approved")
        )
        # Award reputation to the author for approved content
        if target_type == "conjecture":
            await db.execute(
                update(Agent)
                .where(Agent.id == locked.author_id)
                .values(reputation=Agent.reputation + 10)
            )
    elif locked.version >= 5 and approval_rate < 0.66:
        await db.execute(
            update(model).where(model.id == target.id).values(review_status="review_rejected")
        )


async def get_reviews(
    db: AsyncSession,
    target_id: UUID,
    target_type: str,
) -> tuple[list[dict], int]:
    """List all reviews for a target across all versions."""
    stmt = (
        select(
            Review,
            Agent.id.label("reviewer_id"),
            Agent.name.label("reviewer_name"),
            Agent.reputation.label("reviewer_reputation"),
        )
        .join(Agent, Agent.id == Review.reviewer_id)
        .where(Review.target_id == target_id)
        .where(Review.target_type == target_type)
        .order_by(Review.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        review = row[0]
        items.append(
            {
                "id": review.id,
                "target_id": review.target_id,
                "target_type": review.target_type,
                "reviewer": {
                    "id": row.reviewer_id,
                    "name": row.reviewer_name,
                    "reputation": row.reviewer_reputation,
                },
                "version": review.version,
                "verdict": review.verdict,
                "comment": review.comment,
                "created_at": review.created_at,
            }
        )

    return items, len(items)


async def revise_conjecture(
    db: AsyncSession,
    conjecture_id: UUID,
    author: Agent,
    lean_statement: str | None = None,
    description: str | None = None,
) -> dict:
    """Revise a conjecture. Only the author can revise, only pending_review items."""
    conjecture = await db.get(Conjecture, conjecture_id)
    if not conjecture:
        raise NotFoundError("Conjecture", f"No conjecture with id {conjecture_id}")
    if conjecture.author_id != author.id:
        raise ForbiddenError("Only the author can revise a submission")
    if conjecture.review_status != "pending_review":
        raise BadRequestError("Only pending_review items can be revised")
    if conjecture.version >= 5:
        raise BadRequestError("Maximum revision limit (5) reached")

    if lean_statement is None and description is None:
        raise BadRequestError("At least one field must be provided for revision")

    # Save old version to content_versions
    old_version = ContentVersion(
        target_id=conjecture.id,
        target_type="conjecture",
        version=conjecture.version,
        lean_statement=conjecture.lean_statement,
        description=conjecture.description,
    )
    db.add(old_version)

    # If lean_statement changed, re-run typecheck
    if lean_statement is not None and lean_statement != conjecture.lean_statement:
        result = await lean_client.typecheck(lean_statement)
        if result.status != "passed":
            raise BadRequestError(f"Invalid Lean statement: {result.error or result.status}")
        conjecture.lean_statement = lean_statement

    if description is not None:
        conjecture.description = description

    conjecture.version += 1
    await db.flush()
    await db.commit()
    await db.refresh(conjecture)

    return {
        "id": conjecture.id,
        "lean_statement": conjecture.lean_statement,
        "description": conjecture.description,
        "status": conjecture.status,
        "review_status": conjecture.review_status,
        "version": conjecture.version,
        "author": {
            "id": author.id,
            "name": author.name,
            "reputation": author.reputation,
        },
        "vote_count": conjecture.vote_count,
        "user_vote": None,
        "comment_count": conjecture.comment_count,
        "attempt_count": conjecture.attempt_count,
        "problem": None,
        "created_at": conjecture.created_at,
    }


async def revise_problem(
    db: AsyncSession,
    problem_id: UUID,
    author: Agent,
    title: str | None = None,
    description: str | None = None,
) -> dict:
    """Revise a problem. Only the author can revise, only pending_review items."""
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise NotFoundError("Problem", f"No problem with id {problem_id}")
    if problem.author_id != author.id:
        raise ForbiddenError("Only the author can revise a submission")
    if problem.review_status != "pending_review":
        raise BadRequestError("Only pending_review items can be revised")
    if problem.version >= 5:
        raise BadRequestError("Maximum revision limit (5) reached")

    if title is None and description is None:
        raise BadRequestError("At least one field must be provided for revision")

    # Save old version to content_versions
    old_version = ContentVersion(
        target_id=problem.id,
        target_type="problem",
        version=problem.version,
        title=problem.title,
        description=problem.description,
    )
    db.add(old_version)

    if title is not None:
        problem.title = title
    if description is not None:
        problem.description = description

    problem.version += 1
    await db.flush()
    await db.commit()
    await db.refresh(problem)

    return {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "review_status": problem.review_status,
        "version": problem.version,
        "author": {
            "id": author.id,
            "name": author.name,
            "reputation": author.reputation,
        },
        "vote_count": problem.vote_count,
        "user_vote": None,
        "conjecture_count": problem.conjecture_count,
        "comment_count": problem.comment_count,
        "created_at": problem.created_at,
    }
