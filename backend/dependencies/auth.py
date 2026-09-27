"""
dependencies/auth.py

FastAPI dependencies for protecting routes that require authentication.

Usage in a route::

    from dependencies.auth import get_current_user

    @router.get("/protected")
    def protected(user: dict = Depends(get_current_user)):
        user_id = user["user_id"]
        ...

``get_current_user`` extracts the ``Authorization: Bearer <token>`` header,
validates it through ``auth_service.get_user_from_token``, and returns
the full user info dict (user_id, name, email, phone).  Raises 401 when
the token is missing or invalid.

``get_optional_user`` does the same validation but returns ``None``
instead of raising when no token is present — useful for routes that
behave differently in demo mode (no token required) vs live mode
(token required).
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import auth_service, AuthError, ServiceUnavailableError

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    Validate the Bearer token and return the authenticated user's info.

    Returns a dict with keys: user_id, name, email, phone.
    Raises 401 if the token is missing, invalid, or expired.
    Raises 503 if Supabase Auth is not configured.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_info = auth_service.get_user_from_token(credentials.credentials)
    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )

    # Attach the raw token so routes can use it for logout, etc.
    user_info["_access_token"] = credentials.credentials
    return user_info


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> Optional[dict]:
    """
    Return user info if a valid Bearer token is present, else ``None``.

    Used by farmer routes that must work in both demo mode (no auth)
    and live mode (auth required).  The route handler checks the return
    value and decides what to do:

    * ``None`` + DEMO_MODE → serve demo data
    * ``None`` + live mode → return 401
    * ``dict`` → proceed with the authenticated user_id

    If a token IS present but is invalid or Supabase is unreachable,
    this returns ``None`` rather than raising — the route will treat it
    as unauthenticated.  Routes that need strict auth errors should use
    ``get_current_user`` instead.
    """
    if credentials is None:
        return None

    try:
        user_info = auth_service.get_user_from_token(credentials.credentials)
    except (AuthError, ServiceUnavailableError):
        return None

    user_info["_access_token"] = credentials.credentials
    return user_info
