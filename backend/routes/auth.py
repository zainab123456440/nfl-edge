"""
routes/auth.py

Authentication endpoints: signup, login, refresh, logout, password
reset, and /me.

Routes stay thin: they validate input via schemas, delegate to
``auth_service``, and shape the response.  No business logic lives
here (project-context.md, Section 28, rule 6).

Endpoints:
    POST /api/auth/signup                  -> create a new account
    POST /api/auth/login                   -> authenticate
    POST /api/auth/refresh                 -> refresh an expired token
    POST /api/auth/reset-password/request  -> email a reset link
    POST /api/auth/reset-password/confirm  -> set a new password
    POST /api/auth/logout                  -> sign out (protected)
    GET  /api/auth/me                      -> current user info (protected)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from dependencies.auth import get_current_user
from schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignupRequest,
    TokenRefreshRequest,
)
from services.auth_service import (
    auth_service,
    AuthError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exc_to_http(exc: Exception) -> HTTPException:
    """Map service-layer exceptions to the right HTTP status code."""
    if isinstance(exc, AuthError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if isinstance(exc, ServiceUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    logger.exception("Unexpected auth error")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again.",
    )


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest) -> AuthResponse:
    """Create a new Green Flora account."""
    try:
        result = auth_service.signup(payload.name, payload.contact, payload.password)
    except Exception as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    """Authenticate with email + password."""
    try:
        result = auth_service.login(payload.contact, payload.password)
    except Exception as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: TokenRefreshRequest) -> AuthResponse:
    """Exchange a refresh token for a new session."""
    try:
        result = auth_service.refresh(payload.refresh_token)
    except Exception as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


@router.post("/reset-password/request", response_model=MessageResponse)
def request_password_reset(payload: PasswordResetRequest) -> MessageResponse:
    """
    Email the user a password-reset link.

    Always returns the same generic message, whether or not an
    account exists for that email — this avoids leaking which emails
    are registered.
    """
    try:
        auth_service.request_password_reset(payload.contact)
    except AuthError as exc:
        # Bad input (e.g. not an email at all) — safe to surface directly.
        raise _exc_to_http(exc)
    except Exception:
        # Any other failure is swallowed on purpose; see auth_service.
        pass

    return MessageResponse(
        detail="If an account exists for this email, a reset link has been sent."
    )


@router.post("/reset-password/confirm", response_model=MessageResponse)
def confirm_password_reset(payload: PasswordResetConfirmRequest) -> MessageResponse:
    """Set a new password using the token from the emailed reset link."""
    try:
        auth_service.confirm_password_reset(payload.access_token, payload.new_password)
    except Exception as exc:
        raise _exc_to_http(exc)

    return MessageResponse(detail="Password has been reset successfully.")


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

@router.post("/logout")
def logout(user: dict = Depends(get_current_user)):
    """
    Sign out the current user.

    Requires a valid Bearer token.  Logout is best-effort — returns
    200 even if the Supabase sign_out call fails.
    """
    token = user.get("_access_token", "")
    if token:
        try:
            auth_service.logout(token)
        except Exception:
            pass  # best-effort

    return {"detail": "Signed out successfully."}


@router.get("/me", response_model=AuthUserResponse)
def me(user: dict = Depends(get_current_user)) -> AuthUserResponse:
    """Return info about the currently authenticated user."""
    return AuthUserResponse(
        user_id=user["user_id"],
        name=user.get("name"),
        email=user.get("email"),
        phone=user.get("phone"),
    )