"""Loogle search proxy for Mathlib lemma lookup."""

import logging

import httpx
from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentAgent
from app.api.rate_limit import auth_limiter

logger = logging.getLogger(__name__)
router = APIRouter()

LOOGLE_API = "https://loogle.lean-lang.org/api"


@router.get("")
@auth_limiter.limit("60/hour")
async def search_loogle(
    request: Request,
    _agent: CurrentAgent,
    q: str = Query(..., min_length=1, max_length=500, description="Loogle type-pattern query"),
) -> dict:
    """Search Mathlib via Loogle type-pattern matching.

    Example queries:
    - "Antitone _ → Monotone _"
    - "List.map _ _ = _"
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(LOOGLE_API, params={"q": q})
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Loogle returned HTTP {response.status_code}",
                }
            return {"status": "ok", "query": q, "results": response.json()}
    except httpx.TimeoutException:
        return {"status": "error", "error": "Loogle search timed out (30s)"}
    except httpx.HTTPError as e:
        return {"status": "error", "error": f"Failed to reach Loogle: {e}"}
