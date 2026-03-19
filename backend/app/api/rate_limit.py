"""Shared rate-limiting utilities.

IP-keyed limiter: use for unauthenticated endpoints (e.g. registration).
Auth-keyed limiter: use for authenticated endpoints — keys on API key hash
so that per-agent limits are enforced regardless of IP.
"""

import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_api_key_hash(request: Request) -> str:
    """Extract the Bearer token from the Authorization header and return its SHA-256 hash.

    Falls back to remote address if no valid bearer token is present
    (the auth dependency will reject the request anyway).
    """
    auth_header: str | None = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        return hashlib.sha256(token.encode()).hexdigest()
    return get_remote_address(request)


ip_limiter = Limiter(key_func=get_remote_address)
auth_limiter = Limiter(key_func=_get_api_key_hash)
