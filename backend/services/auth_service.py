"""
auth_service.py

Business logic for authentication via Supabase Auth.

This is the ONLY module that talks to Supabase Auth directly.  Routes
call these methods and never touch the Supabase client themselves.

When Supabase is not configured (fresh clone, demo mode), signup and
login return a ``ServiceUnavailableError`` so the route layer can
respond with a friendly message instead of crashing.

NOTE: Phone-based signup/login has been intentionally disabled.
Supabase requires a paid SMS provider (Twilio, etc.) to verify phone
numbers, which this project does not use. Only email + password is
supported. If phone auth is reintroduced later, restore the branches
that call supabase.auth.sign_up / sign_in_with_password with a
"phone" key, and re-enable phone confirmations in the Supabase
dashboard (Authentication -> Providers -> Phone).

Password reset flow:
    1. Frontend calls request_password_reset(email). Supabase emails
       the user a link to FRONTEND_URL/reset-password containing a
       recovery access_token (in the URL fragment).
    2. The reset-password page reads that token and posts it, along
       with the new password, to confirm_password_reset().
    3. We verify the token identifies a real user, then use the
       Supabase *admin* API to set the new password directly (this
       requires the service-role key, not the anon key).

Requires ``settings.frontend_url`` to be set (e.g.
"https://green-flora.vercel.app" in production, "http://localhost:3000"
in dev) so Supabase knows where to send the user after they click the
reset link. Defaults to the production Vercel URL in config/settings.py
if the FRONTEND_URL environment variable isn't set.
"""

import logging
from typing import Optional

from config.settings import settings
from config.supabase_client import supabase
from schemas.auth import is_email

logger = logging.getLogger(__name__)


class ServiceUnavailableError(Exception):
    """Raised when Supabase is not configured or unreachable."""


class AuthError(Exception):
    """Raised when authentication fails for a known reason."""


class AuthService:
    """Handles signup, login, token refresh, password reset, and user lookup."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_client(self):
        """Raise if the Supabase client was never initialised."""
        if supabase is None:
            raise ServiceUnavailableError(
                "Authentication service is not configured. "
                "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def signup(self, name: str, contact: str, password: str) -> dict:
        """
        Create a new Supabase Auth user.

        Email signup only — phone signup is disabled (requires a paid
        SMS provider we don't use).

        Returns a dict with keys: access_token, refresh_token, user_id,
        name, is_new.
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError("Please sign up with an email address.")

        options = {"data": {"name": name}}  # stored in user_metadata

        try:
            response = supabase.auth.sign_up(
                {"email": contact, "password": password, "options": options}
            )
        except Exception as exc:
            logger.warning("Supabase signup failed: %s", exc)
            message = str(exc)
            if "already registered" in message.lower() or "already" in message.lower():
                raise AuthError("An account with this contact already exists.")
            raise AuthError("Could not create account. Please try again.")

        session = response.session
        if session is None:
            # Email confirmation might be enabled — still return useful info.
            user = response.user
            raise AuthError(
                "Account created. Please check your email to confirm."
            )

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": session.user.id,
            "name": name,
            "is_new": True,
        }

    def login(self, contact: str, password: str) -> dict:
        """
        Authenticate an existing user.

        Email login only — phone login is disabled (requires a paid
        SMS provider we don't use).

        Returns the same dict shape as signup().
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError("Please sign in with your email address.")

        try:
            response = supabase.auth.sign_in_with_password(
                {"email": contact, "password": password}
            )
        except Exception as exc:
            logger.warning("Supabase login failed: %s", exc)
            raise AuthError("Invalid credentials. Please try again.")

        session = response.session
        user = session.user
        name = (user.user_metadata or {}).get("name")

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "name": name,
            "is_new": False,
        }

    def refresh(self, refresh_token: str) -> dict:
        """
        Exchange a refresh token for a new session.

        Returns the standard auth dict.
        """
        self._ensure_client()

        try:
            response = supabase.auth.refresh_session(refresh_token)
        except Exception as exc:
            logger.warning("Supabase token refresh failed: %s", exc)
            raise AuthError("Session expired. Please sign in again.")

        session = response.session
        if session is None:
            raise AuthError("Session expired. Please sign in again.")

        user = session.user
        name = (user.user_metadata or {}).get("name")

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "name": name,
            "is_new": False,
        }

    def request_password_reset(self, contact: str) -> None:
        """
        Send a password-reset email via Supabase.

        Always treat this as best-effort from the caller's perspective:
        the route layer should return the same generic success message
        whether or not the email exists, to avoid leaking which emails
        are registered. We still raise AuthError for genuinely bad
        input (e.g. not an email) so the form can show a useful message.

        NOTE: Config/setup failures (bad settings, Supabase misconfig,
        network errors) are logged at ERROR level, not swallowed
        silently at WARNING — those are bugs, not "email doesn't
        exist" cases, and should be loud in logs/alerts even though
        the caller still gets a generic success response.
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError("Please enter the email address for your account.")

        # NOTE: settings.py defines this as `frontend_url` (lowercase).
        # A previous version of this line read `settings.FRONTEND_URL`
        # (uppercase), which doesn't exist on the Settings object and
        # raised an AttributeError on every call — silently swallowed
        # below, so no reset email was ever actually sent. Keep this
        # attribute name in sync with config/settings.py.
        redirect_to = f"{settings.frontend_url.rstrip('/')}/reset-password"

        try:
            supabase.auth.reset_password_for_email(
                contact,
                {"redirect_to": redirect_to},
            )
        except Exception as exc:
            # Don't tell the caller whether the email exists — but do
            # log loudly, since most failures here are config/bugs,
            # not "email not found" (Supabase doesn't error for that).
            logger.error(
                "Password reset email failed to send for %s: %s",
                contact,
                exc,
                exc_info=True,
            )

    def confirm_password_reset(self, access_token: str, new_password: str) -> None:
        """
        Finalize a password reset using the recovery access_token from
        the emailed reset link, plus a new password chosen by the user.
        """
        self._ensure_client()

        try:
            user_response = supabase.auth.get_user(access_token)
            user_id = user_response.user.id
        except Exception as exc:
            logger.warning("Invalid or expired password reset token: %s", exc)
            raise AuthError(
                "This reset link is invalid or has expired. Please request a new one."
            )

        try:
            supabase.auth.admin.update_user_by_id(
                user_id, {"password": new_password}
            )
        except Exception as exc:
            logger.warning("Supabase password update failed: %s", exc)
            raise AuthError("Could not reset password. Please try again.")

    def get_user_from_token(self, access_token: str) -> dict:
        """
        Verify a JWT access token and return user info.

        Returns a dict with: user_id, name, email, phone.
        """
        self._ensure_client()

        try:
            response = supabase.auth.get_user(access_token)
        except Exception as exc:
            logger.warning("Supabase get_user failed: %s", exc)
            raise AuthError("Invalid or expired token.")

        user = response.user
        metadata = user.user_metadata or {}

        return {
            "user_id": user.id,
            "name": metadata.get("name"),
            "email": user.email,
            "phone": user.phone,
        }

    def logout(self, access_token: str) -> None:
        """Sign out the user associated with the given token."""
        self._ensure_client()

        try:
            supabase.auth.sign_out(access_token)
        except Exception as exc:
            # Logout is best-effort — don't raise on failure.
            logger.warning("Supabase logout failed (non-critical): %s", exc)


# Single shared instance.
auth_service = AuthService()