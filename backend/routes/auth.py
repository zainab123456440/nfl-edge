"""
routes/auth.py

Authentication endpoints:
- signup
- login
- refresh
- logout
- password reset
- current authenticated user

Routes stay thin. Authentication/business logic belongs to
services.auth_service and dependencies.auth.
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
    AuthError,
    ServiceUnavailableError,
    auth_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exc_to_http(exc: Exception) -> HTTPException:
    """Map service-layer exceptions to appropriate HTTP responses."""
    if isinstance(exc, AuthError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, ServiceUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )

    logger.exception("Unexpected authentication error")

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again.",
    )


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/signup",
    response_model=AuthResponse,
)
def signup(payload: SignupRequest) -> AuthResponse:
    """Create a new account."""
    try:
        result = auth_service.signup(
            payload.name,
            payload.contact,
            payload.password,
        )
    except (AuthError, ServiceUnavailableError) as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(payload: LoginRequest) -> AuthResponse:
    """Authenticate with email and password."""
    try:
        result = auth_service.login(
            payload.contact,
            payload.password,
        )
    except (AuthError, ServiceUnavailableError) as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


@router.post(
    "/refresh",
    response_model=AuthResponse,
)
def refresh(payload: TokenRefreshRequest) -> AuthResponse:
    """Exchange a refresh token for a new authenticated session."""
    try:
        result = auth_service.refresh(
            payload.refresh_token,
        )
    except (AuthError, ServiceUnavailableError) as exc:
        raise _exc_to_http(exc)

    return AuthResponse(**result)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post(
    "/reset-password/request",
    response_model=MessageResponse,
)
def request_password_reset(
    payload: PasswordResetRequest,
) -> MessageResponse:
    """
    Request a password-reset email.

    Always returns the same generic response so the endpoint does not
    reveal whether an email address is registered.
    """
    try:
        auth_service.request_password_reset(
            payload.contact,
        )
    except AuthError as exc:
        # Invalid input such as a malformed email is safe to expose.
        raise _exc_to_http(exc)
    except ServiceUnavailableError:
        # Keep account enumeration protection while still logging the
        # infrastructure problem.
        logger.exception(
            "Password reset service unavailable"
        )
    except Exception:
        # Password-reset requests must not reveal account existence or
        # internal service details.
        logger.exception(
            "Unexpected password reset request error"
        )

    return MessageResponse(
        detail=(
            "If an account exists for this email, "
            "a reset link has been sent."
        )
    )


@router.post(
    "/reset-password/confirm",
    response_model=MessageResponse,
)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
) -> MessageResponse:
    """Set a new password using the recovery token."""
    try:
        auth_service.confirm_password_reset(
            payload.access_token,
            payload.new_password,
        )
    except (AuthError, ServiceUnavailableError) as exc:
        raise _exc_to_http(exc)

    return MessageResponse(
        detail="Password has been reset successfully."
    )


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

@router.post("/logout")
def logout(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Sign out the currently authenticated user.

    The token is taken from the validated authentication dependency,
    never from a request-body or query-string user ID.
    """
    access_token = user.get("_access_token")

    if access_token:
        try:
            auth_service.logout(access_token)
        except ServiceUnavailableError:
            logger.warning(
                "Authentication service unavailable during logout."
            )
        except Exception:
            # Logout remains best-effort.
            logger.exception(
                "Unexpected error during logout."
            )

    return {
        "detail": "Signed out successfully."
    }


@router.get(
    "/me",
    response_model=AuthUserResponse,
)
def me(
    user: dict = Depends(get_current_user),
) -> AuthUserResponse:
    """
    Return the currently authenticated user's information.

    The identity comes entirely from the validated Bearer token.
    """
    return AuthUserResponse(
        user_id=user["user_id"],
        name=user.get("name"),
        email=user.get("email"),
        
    )