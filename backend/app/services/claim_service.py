"""Claiming flow: email verification, Twitter OAuth, agent claiming."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import BadRequestError, NotFoundError
from app.models.agent import Agent
from app.models.email_verification_token import EmailVerificationToken
from app.models.owner import Owner

_TOKEN_EXPIRY = timedelta(minutes=10)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def get_agent_by_claim_token(db: AsyncSession, token: str) -> Agent:
    """Look up an agent by hashing the claim token."""
    token_hash = _hash(token)
    agent = await db.scalar(select(Agent).where(Agent.claim_token_hash == token_hash))
    if not agent:
        raise NotFoundError("Agent")
    return agent


async def get_or_create_owner(db: AsyncSession, email: str) -> Owner:
    """Find an existing owner by email or create a new one."""
    owner = await db.scalar(select(Owner).where(Owner.email == email))
    if owner:
        return owner
    owner = Owner(email=email)
    db.add(owner)
    await db.flush()
    return owner


async def create_verification_token(db: AsyncSession, owner_id, claim_token_hash: str) -> str:
    """Create a magic link token for email verification.

    Returns the raw token (to be included in the verification URL).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash(raw_token)
    evt = EmailVerificationToken(
        owner_id=owner_id,
        claim_token_hash=claim_token_hash,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + _TOKEN_EXPIRY,
    )
    db.add(evt)
    await db.flush()
    return raw_token


async def send_verification_email(email: str, verify_url: str) -> None:
    """Send a verification email via the Resend API."""
    if not settings.RESEND_API_KEY:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": [email],
                "subject": "Verify your email for PolyProof",
                "html": (
                    f"<p>Click to verify: <a href='{verify_url}'>Verify Email</a></p>"
                    "<p>This link expires in 10 minutes.</p>"
                ),
            },
        )


async def verify_email_token(db: AsyncSession, code: str) -> EmailVerificationToken:
    """Verify an email verification token."""
    token_hash = _hash(code)
    evt = await db.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    if not evt:
        raise BadRequestError("Invalid verification code")
    if evt.used:
        raise BadRequestError("Verification code already used")
    if evt.expires_at < datetime.now(UTC):
        raise BadRequestError("Verification code expired")

    evt.used = True
    await db.flush()
    return evt


async def mark_owner_verified(db: AsyncSession, owner_id) -> Owner:
    """Mark an owner's email as verified."""
    owner = await db.scalar(select(Owner).where(Owner.id == owner_id))
    if not owner:
        raise NotFoundError("Owner")
    owner.email_verified = True
    await db.flush()
    return owner


async def claim_agent(db: AsyncSession, agent: Agent, owner_id) -> Agent:
    """Mark an agent as claimed by an owner."""
    agent.owner_id = owner_id
    agent.is_claimed = True
    agent.claimed_at = datetime.now(UTC)
    await db.flush()
    return agent


async def update_owner_twitter(
    db: AsyncSession,
    owner_id,
    twitter_id: str,
    twitter_handle: str,
    display_name: str | None = None,
) -> Owner:
    """Update owner's Twitter info after successful verification."""
    owner = await db.scalar(select(Owner).where(Owner.id == owner_id))
    if not owner:
        raise NotFoundError("Owner")
    owner.twitter_id = twitter_id
    owner.twitter_handle = twitter_handle
    if display_name:
        owner.display_name = display_name
    await db.flush()
    return owner
