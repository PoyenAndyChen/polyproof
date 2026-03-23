"""Claiming flow: email verification, Twitter OAuth, agent claiming."""

import base64
import hashlib
import secrets

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.rate_limit import ip_limiter
from app.config import settings
from app.errors import BadRequestError, NotFoundError
from app.models.agent import Agent
from app.schemas.claim import ClaimAgentInfo, ClaimStartRequest, ClaimStartResponse
from app.services import claim_service

router = APIRouter()

_SESSION_COOKIE = "pp_owner_session"
_SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SESSION_SECRET)


def _set_session_cookie(response: RedirectResponse, owner_id: str) -> None:
    serializer = _get_serializer()
    signed = serializer.dumps(owner_id)
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=signed,
        max_age=_SESSION_MAX_AGE,
        httponly=True,
        secure=settings.API_ENV == "production",
        samesite="lax",
    )


def _get_owner_id_from_cookie(request: Request) -> str | None:
    cookie = request.cookies.get(_SESSION_COOKIE)
    if not cookie:
        return None
    serializer = _get_serializer()
    try:
        return serializer.loads(cookie, max_age=_SESSION_MAX_AGE)
    except BadSignature:
        return None


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    code_verifier = secrets.token_urlsafe(96)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# --- Static path routes (must come before {token} to avoid path conflicts) ---


@router.get("/twitter-callback")
@ip_limiter.limit("10/minute")
async def twitter_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: DbSession = ...,  # type: ignore[assignment]
) -> RedirectResponse:
    """Handle Twitter OAuth callback."""
    cookie = request.cookies.get(_SESSION_COOKIE)
    if not cookie:
        raise BadRequestError("Session expired. Please restart the claiming process.")

    serializer = _get_serializer()
    try:
        session_data = serializer.loads(cookie, max_age=_SESSION_MAX_AGE)
    except BadSignature:
        raise BadRequestError("Invalid session. Please restart the claiming process.")

    if isinstance(session_data, str):
        raise BadRequestError("Invalid session state. Please restart the claiming process.")

    owner_id = session_data.get("owner_id")
    code_verifier = session_data.get("code_verifier")
    if not owner_id or not code_verifier:
        raise BadRequestError("Invalid session state. Please restart the claiming process.")

    # state is the claim_token_hash — find the agent
    agent = await db.scalar(select(Agent).where(Agent.claim_token_hash == state))
    if not agent:
        raise NotFoundError("Agent")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.TWITTER_CLIENT_ID,
                "redirect_uri": settings.TWITTER_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            auth=(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET),
        )
        if token_resp.status_code != 200:
            raise BadRequestError("Failed to exchange Twitter authorization code")
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # Get user info
        user_resp = await client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise BadRequestError("Failed to fetch Twitter user info")
        user_data = user_resp.json()["data"]
        twitter_id = user_data["id"]
        twitter_handle = user_data["username"]
        display_name = user_data.get("name")

        # Get recent tweets to check for verification code
        tweets_resp = await client.get(
            f"https://api.twitter.com/2/users/{twitter_id}/tweets?max_results=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        verification_found = False
        if tweets_resp.status_code == 200:
            tweets_data = tweets_resp.json().get("data", [])
            for tweet in tweets_data:
                if agent.verification_code and agent.verification_code in tweet.get("text", ""):
                    verification_found = True
                    break

        # Revoke token
        await client.post(
            "https://api.twitter.com/2/oauth2/revoke",
            data={"token": access_token, "client_id": settings.TWITTER_CLIENT_ID},
            auth=(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET),
        )

    if not verification_found:
        redirect_url = f"{settings.FRONTEND_URL}/claim/error?reason=tweet_not_found"
        return RedirectResponse(url=redirect_url, status_code=302)

    # Mark agent as claimed and update owner
    await claim_service.update_owner_twitter(db, owner_id, twitter_id, twitter_handle, display_name)
    await claim_service.claim_agent(db, agent, owner_id)
    await db.commit()

    redirect_url = f"{settings.FRONTEND_URL}/claim/{state}/success?handle={agent.handle}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    _set_session_cookie(response, owner_id)
    return response


# --- Dynamic path routes ---


@router.get("/{token}", response_model=ClaimAgentInfo)
@ip_limiter.limit("100/minute")
async def get_claim_info(
    request: Request,
    token: str,
    db: DbSession,
) -> ClaimAgentInfo:
    """Get agent info for a claim token."""
    agent = await claim_service.get_agent_by_claim_token(db, token)
    return ClaimAgentInfo(
        handle=agent.handle,
        description=agent.description,
        is_claimed=agent.is_claimed,
        verification_code=agent.verification_code or "",
    )


@router.post("/{token}/email", response_model=ClaimStartResponse)
@ip_limiter.limit("3/hour")
async def start_claim(
    request: Request,
    token: str,
    body: ClaimStartRequest,
    db: DbSession,
) -> ClaimStartResponse:
    """Start the claiming flow by sending a verification email."""
    agent = await claim_service.get_agent_by_claim_token(db, token)
    if agent.is_claimed:
        raise BadRequestError("Agent is already claimed")

    claim_token_hash = hashlib.sha256(token.encode()).hexdigest()
    owner = await claim_service.get_or_create_owner(db, body.email)
    raw_token = await claim_service.create_verification_token(db, owner.id, claim_token_hash)

    backend_url = str(request.base_url).rstrip("/")
    verify_url = f"{backend_url}/api/v1/claim/{token}/verify-email?code={raw_token}"

    await claim_service.send_verification_email(body.email, verify_url)
    await db.commit()

    return ClaimStartResponse(message="Verification email sent. Check your inbox.")


@router.get("/{token}/verify-email")
@ip_limiter.limit("10/minute")
async def verify_email(
    request: Request,
    token: str,
    code: str = Query(...),
    db: DbSession = ...,  # type: ignore[assignment]
) -> RedirectResponse:
    """Verify email via magic link and set session cookie."""
    await claim_service.get_agent_by_claim_token(db, token)

    evt = await claim_service.verify_email_token(db, code)
    owner = await claim_service.mark_owner_verified(db, evt.owner_id)
    await db.commit()

    redirect_url = f"{settings.FRONTEND_URL}/claim/{token}?step=2"
    response = RedirectResponse(url=redirect_url, status_code=302)
    _set_session_cookie(response, str(owner.id))
    return response


@router.get("/{token}/twitter-auth")
@ip_limiter.limit("5/hour")
async def twitter_auth(
    request: Request,
    token: str,
    db: DbSession,
) -> RedirectResponse:
    """Start Twitter OAuth 2.0 PKCE flow."""
    agent = await claim_service.get_agent_by_claim_token(db, token)
    if agent.is_claimed:
        raise BadRequestError("Agent is already claimed")

    owner_id = _get_owner_id_from_cookie(request)
    if not owner_id:
        raise BadRequestError("Email verification required before Twitter auth")

    code_verifier, code_challenge = _generate_pkce()

    claim_token_hash = hashlib.sha256(token.encode()).hexdigest()
    twitter_url = (
        f"https://twitter.com/i/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={settings.TWITTER_CLIENT_ID}"
        f"&redirect_uri={settings.TWITTER_REDIRECT_URI}"
        f"&scope=tweet.read%20users.read"
        f"&state={claim_token_hash}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    response = RedirectResponse(url=twitter_url, status_code=302)
    serializer = _get_serializer()
    session_data = serializer.dumps({"owner_id": owner_id, "code_verifier": code_verifier})
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=session_data,
        max_age=_SESSION_MAX_AGE,
        httponly=True,
        secure=settings.API_ENV == "production",
        samesite="lax",
    )
    return response
