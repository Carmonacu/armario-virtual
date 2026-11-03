"""Verify Supabase Auth access tokens.

Current projects sign session JWTs with an asymmetric key published at
``{SUPABASE_URL}/auth/v1/.well-known/jwks.json`` (ES256 or RS256). Projects that
have not rotated off the legacy shared secret still send HS256; those verify
with ``SUPABASE_JWT_SECRET``. Claims that the user can edit (``user_metadata``)
are never used for authorization.
"""

from __future__ import annotations

import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import get_settings

logger = logging.getLogger(__name__)

_ASYMMETRIC = frozenset({"ES256", "RS256", "EdDSA"})
_jwks_clients: dict[str, PyJWKClient] = {}


class SupabaseTokenError(Exception):
    """The bearer token is not a valid Supabase user access token."""


def supabase_issuer(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1"


def _jwks_client(supabase_url: str) -> PyJWKClient:
    issuer = supabase_issuer(supabase_url)
    client = _jwks_clients.get(issuer)
    if client is None:
        client = PyJWKClient(
            f"{issuer}/.well-known/jwks.json",
            cache_keys=True,
            lifespan=600,
        )
        _jwks_clients[issuer] = client
    return client


def verify_supabase_access_token(token: str) -> dict[str, Any]:
    """Return verified claims or raise SupabaseTokenError.

    Requires ``role=authenticated`` and an email claim. Anonymous and
    service-role tokens are rejected: the API is publicly reachable.
    """
    settings = get_settings()
    if not settings.supabase_url:
        raise SupabaseTokenError("Supabase auth is not configured")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise SupabaseTokenError("Malformed token") from exc

    algorithm = header.get("alg")
    issuer = supabase_issuer(settings.supabase_url)
    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise SupabaseTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
        key: Any = settings.supabase_jwt_secret
        algorithms = ["HS256"]
    elif algorithm in _ASYMMETRIC:
        try:
            key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
        except Exception as exc:
            raise SupabaseTokenError("Could not load the Supabase signing key") from exc
        algorithms = [algorithm]
    else:
        raise SupabaseTokenError("Unsupported token algorithm")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise SupabaseTokenError("Invalid or expired Supabase token") from exc

    if claims.get("role") != "authenticated":
        raise SupabaseTokenError("Token is not an authenticated user session")
    if claims.get("is_anonymous") is True:
        raise SupabaseTokenError("Anonymous Supabase users cannot sign in")
    email = claims.get("email")
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise SupabaseTokenError("Token is missing a subject")
    if not isinstance(email, str) or "@" not in email:
        raise SupabaseTokenError("Token is missing an email claim")
    return claims
