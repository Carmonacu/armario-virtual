from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.database import DbSession
from app.models.user import User
from app.schemas.auth import AuthSession, TokenPayload
from app.services.user_service import FORWARD_AUTH, UserEmailConflictError, UserService
from app.utils.forward_auth import (
    FORWARD_AUTH_SECRET_HEADER,
    forward_auth_secret_matches,
    proxy_header,
    single_header,
)
from app.utils.supabase_jwt import SupabaseTokenError, verify_supabase_access_token

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)


def try_decode_app_token(token: str) -> TokenPayload | None:
    """Decode a token this API minted. Returns None when it is not one of ours."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )
        return TokenPayload(**payload)
    except jwt.PyJWTError:
        return None
    except Exception:
        return None


def decode_token(token: str) -> TokenPayload:
    payload = try_decode_app_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _user_from_bearer(token: str, db: DbSession) -> User | None:
    """Resolve an app-minted token or, when configured, a Supabase access token.

    A token this API signed but that matches no user returns None (the caller
    answers 401 Not authenticated). Anything else that does not verify raises
    401 Invalid or expired token, including a Supabase JWT with a bad signature.
    """
    user_service = UserService(db)
    app_token = try_decode_app_token(token)
    if app_token is not None:
        return await user_service.get_by_token(app_token)
    if not settings.supabase_configured:
        raise _invalid_token()
    try:
        claims = verify_supabase_access_token(token)
    except SupabaseTokenError:
        raise _invalid_token() from None
    try:
        return await user_service.user_from_supabase(claims)
    except UserEmailConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


async def get_current_user_optional(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User | None:
    if not credentials:
        return None

    try:
        user_service = UserService(db)
        user = await _user_from_bearer(credentials.credentials, db)
    except HTTPException:
        return None
    # A deactivated account or a switched proxy user is treated as anonymous, as
    # get_current_user refuses both.
    if user is None or not user.is_active:
        return None
    if await _proxy_user_switched(request, user, user_service):
        return None
    return user


# The browser reaches /api/v1 straight through nginx or the ingress, past the frontend middleware
# that ends a session when the proxy user changes, so a request the proxy vouched for is checked here.
async def _proxy_user_switched(request: Request, user: User, user_service: UserService) -> bool:
    presented_secret = single_header(request.headers, FORWARD_AUTH_SECRET_HEADER)
    if not forward_auth_secret_matches(presented_secret, settings.forward_auth_secret):
        return False
    remote_user = proxy_header(request.headers, "Remote-User")
    return bool(remote_user) and not await user_service.holds_identity(
        user.id, FORWARD_AUTH, remote_user
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    user_service = UserService(db)
    user = None

    if credentials:
        user = await _user_from_bearer(credentials.credentials, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if await _proxy_user_switched(request, user, user_service):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The signed-in user changed at the proxy. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_session(
    user: Annotated[User, Depends(get_current_user)],
) -> AuthSession:
    return AuthSession(
        user_id=user.id,
        external_id=user.external_id,
        email=user.email,
        display_name=user.display_name,
        family_id=user.family_id,
        role=user.role,
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentSession = Annotated[AuthSession, Depends(get_current_session)]
WriteUser = CurrentUser
