"""
auth.py (schemas)

Request/response schemas for authentication endpoints.

Follows the same separation pattern as schemas/farmer.py: these are
the EXTERNAL shapes exposed over the API.  The internal auth logic
lives in services/auth_service.py.

The ``contact`` field in signup/login now only accepts an email
address. Phone-based signup/login has been intentionally disabled
because it requires a paid SMS provider (Twilio, etc.) on the
Supabase side, which this project does not use. If phone auth is
reintroduced later, restore the ``is_phone`` check in
``validate_contact`` below.
"""

import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Rough check — not a full E.164 validator, but catches obvious junk.
# Kept for potential future use (e.g. /me response, display formatting)
# even though phone signup/login is currently disabled.
_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def is_email(value: str) -> bool:
    """Return True if the value looks like an email (contains @)."""
    return "@" in value


def is_phone(value: str) -> bool:
    """Return True if the value looks like a phone number."""
    return bool(_PHONE_RE.match(value.strip()))


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    """Payload for POST /api/auth/signup."""

    name: str = Field(min_length=1, max_length=100)
    contact: str = Field(
        min_length=3,
        max_length=100,
        description="Email address. Phone signup is disabled.",
    )
    password: str = Field(min_length=8, max_length=128)

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value: str) -> str:
        value = value.strip()
        if not is_email(value):
            raise ValueError("Enter a valid email address.")
        return value


class LoginRequest(BaseModel):
    """Payload for POST /api/auth/login."""

    contact: str = Field(
        min_length=3,
        max_length=100,
        description="Email address used at signup. Phone login is disabled.",
    )
    password: str = Field(min_length=1)

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value: str) -> str:
        value = value.strip()
        if not is_email(value):
            raise ValueError("Enter a valid email address.")
        return value


class TokenRefreshRequest(BaseModel):
    """Payload for POST /api/auth/refresh."""

    refresh_token: str = Field(min_length=1)


class PasswordResetRequest(BaseModel):
    """Payload for POST /api/auth/reset-password/request."""

    contact: str = Field(
        min_length=3,
        max_length=100,
        description="Email address associated with the account.",
    )

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value: str) -> str:
        value = value.strip()
        if not is_email(value):
            raise ValueError("Enter a valid email address.")
        return value


class PasswordResetConfirmRequest(BaseModel):
    """Payload for POST /api/auth/reset-password/confirm."""

    access_token: str = Field(
        min_length=1,
        description="Recovery token from the emailed reset link.",
    )
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class AuthResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    refresh_token: str
    user_id: str
    name: Optional[str] = None
    is_new: bool = False


class AuthUserResponse(BaseModel):
    """Response for GET /api/auth/me — current user info."""

    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic message response, e.g. for password reset endpoints."""

    detail: str