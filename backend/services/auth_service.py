"""
services/auth_service.py

Business logic for authentication via Supabase Auth.

This is the ONLY module that talks to Supabase Auth directly. Routes
call these methods and never access Supabase Auth themselves.

Security rules:
- User identity comes from Supabase Auth.
- Never trust a user_id supplied by the frontend.
- Access tokens are validated through Supabase Auth.
- User-specific backend routes should derive ownership from
  get_user_from_token().
"""

import logging

from config.settings import settings
from config.supabase_client import supabase
from schemas.auth import is_email

logger = logging.getLogger(__name__)


class ServiceUnavailableError(Exception):
    """Raised when Supabase is not configured or unavailable."""


class AuthError(Exception):
    """Raised when authentication fails for a known reason."""


class AuthService:
    """Handles signup, login, refresh, password reset, and user lookup."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_client(self):
        """Ensure the Supabase client is initialized."""
        if supabase is None:
            raise ServiceUnavailableError(
                "Authentication service is not configured. "
                "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )

    @staticmethod
    def _user_name(user) -> str | None:
        """Safely extract the user's display name from metadata."""
        metadata = getattr(user, "user_metadata", None) or {}
        name = metadata.get("name")
        return str(name) if name is not None else None

    @staticmethod
    def _session_user(session):
        """
        Return the authenticated user from a Supabase session.

        Raises AuthError rather than allowing an unexpected NoneType
        exception to leak into the API.
        """
        if session is None:
            raise AuthError("Session expired. Please sign in again.")

        user = getattr(session, "user", None)

        if user is None or not getattr(user, "id", None):
            raise AuthError("Authentication failed. Please sign in again.")

        return user

    @staticmethod
    def _auth_response(response):
        """Safely extract a valid session from a Supabase auth response."""
        session = getattr(response, "session", None)

        if session is None:
            raise AuthError("Authentication failed. Please try again.")

        return session

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    def signup(self, name: str, contact: str, password: str) -> dict:
        """
        Create a new Supabase Auth user.

        Email signup only.

        Returns:
            access_token
            refresh_token
            user_id
            name
            is_new
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError("Please sign up with an email address.")

        clean_name = name.strip()
        clean_contact = contact.strip().lower()

        if not clean_name:
            raise AuthError("Please enter your name.")

        options = {
            "data": {
                "name": clean_name,
            }
        }

        try:
            response = supabase.auth.sign_up(
                {
                    "email": clean_contact,
                    "password": password,
                    "options": options,
                }
            )
        except Exception as exc:
            logger.warning("Supabase signup failed: %s", exc)

            message = str(exc).lower()

            if (
                "already registered" in message
                or "already exists" in message
                or "already been registered" in message
            ):
                raise AuthError(
                    "An account with this contact already exists."
                )

            raise AuthError(
                "Could not create account. Please try again."
            )

        user = getattr(response, "user", None)
        session = getattr(response, "session", None)

        if user is None or not getattr(user, "id", None):
            raise AuthError(
                "Could not create account. Please try again."
            )

        if session is None:
            # Email confirmation may be enabled in Supabase.
            raise AuthError(
                "Account created. Please check your email to confirm."
            )

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "name": clean_name,
            "is_new": True,
        }

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self, contact: str, password: str) -> dict:
        """
        Authenticate an existing user.

        Email login only.

        Returns the same dictionary shape as signup().
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError("Please sign in with your email address.")

        clean_contact = contact.strip().lower()

        try:
            response = supabase.auth.sign_in_with_password(
                {
                    "email": clean_contact,
                    "password": password,
                }
            )
        except Exception as exc:
            logger.warning("Supabase login failed: %s", exc)
            raise AuthError(
                "Invalid credentials. Please try again."
            )

        session = self._auth_response(response)
        user = self._session_user(session)

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "name": self._user_name(user),
            "is_new": False,
        }

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, refresh_token: str) -> dict:
        """
        Exchange a refresh token for a new authenticated session.
        """
        self._ensure_client()

        if not refresh_token:
            raise AuthError("Refresh token is required.")

        try:
            response = supabase.auth.refresh_session(refresh_token)
        except Exception as exc:
            logger.warning("Supabase token refresh failed: %s", exc)
            raise AuthError(
                "Session expired. Please sign in again."
            )

        session = self._auth_response(response)
        user = self._session_user(session)

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "name": self._user_name(user),
            "is_new": False,
        }

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def request_password_reset(self, contact: str) -> None:
        """
        Send a password-reset email through Supabase.

        The caller should return a generic success response regardless
        of whether the email exists, preventing account enumeration.
        """
        self._ensure_client()

        if not is_email(contact):
            raise AuthError(
                "Please enter the email address for your account."
            )

        clean_contact = contact.strip().lower()

        redirect_to = (
            f"{settings.frontend_url.rstrip('/')}/reset-password"
        )

        try:
            supabase.auth.reset_password_for_email(
                clean_contact,
                {
                    "redirect_to": redirect_to,
                },
            )
        except Exception as exc:
            logger.error(
                "Password reset email failed to send for %s: %s",
                clean_contact,
                exc,
                exc_info=True,
            )

    def confirm_password_reset(
        self,
        access_token: str,
        new_password: str,
    ) -> None:
        """
        Validate the recovery access token and update the user's password.
        """
        self._ensure_client()

        if not access_token:
            raise AuthError(
                "This reset link is invalid or has expired. "
                "Please request a new one."
            )

        if not new_password:
            raise AuthError("Please enter a new password.")

        try:
            user_response = supabase.auth.get_user(access_token)
            user = getattr(user_response, "user", None)

            if user is None or not getattr(user, "id", None):
                raise AuthError(
                    "This reset link is invalid or has expired. "
                    "Please request a new one."
                )

            user_id = user.id

        except AuthError:
            raise
        except Exception as exc:
            logger.warning(
                "Invalid or expired password reset token: %s",
                exc,
            )
            raise AuthError(
                "This reset link is invalid or has expired. "
                "Please request a new one."
            )

        try:
            supabase.auth.admin.update_user_by_id(
                user_id,
                {
                    "password": new_password,
                },
            )
        except Exception as exc:
            logger.warning(
                "Supabase password update failed: %s",
                exc,
            )
            raise AuthError(
                "Could not reset password. Please try again."
            )

    # ------------------------------------------------------------------
    # Token validation / current user
    # ------------------------------------------------------------------

    def get_user_from_token(self, access_token: str) -> dict:
        """
        Validate an access token through Supabase Auth.

        This is the backend source of truth for the authenticated user.

        Returns:
            {
                "user_id": "...",
                "name": "...",
                "email": "...",
                "phone": "..."
            }
        """
        self._ensure_client()

        if not access_token:
            raise AuthError("Invalid or expired token.")

        try:
            response = supabase.auth.get_user(access_token)
        except Exception as exc:
            logger.warning(
                "Supabase get_user failed: %s",
                exc,
            )
            raise AuthError("Invalid or expired token.")

        user = getattr(response, "user", None)

        if user is None or not getattr(user, "id", None):
            raise AuthError("Invalid or expired token.")

        metadata = getattr(user, "user_metadata", None) or {}

        return {
            "user_id": str(user.id),
            "name": metadata.get("name"),
            "email": getattr(user, "email", None),
            "phone": getattr(user, "phone", None),
        }

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self, access_token: str) -> None:
        """
        Revoke the session that belongs to the supplied access token.

        Logout is intentionally best-effort. The frontend should still
        clear its local tokens even if the remote logout call fails.
        """
        self._ensure_client()

        if not access_token:
            return

        try:
            # The admin sign-out takes the user's JWT string.
            # "local" ends only this session; use "global" to sign the
            # user out of every device.
            #
            # Do NOT call supabase.auth.sign_out(access_token) here:
            # sign_out() expects an options dict, not a token string,
            # which caused "string indices must be integers".
            supabase.auth.admin.sign_out(access_token, "local")
        except Exception as exc:
            logger.warning(
                "Supabase logout failed (non-critical): %s",
                exc,
            )


# Single shared instance.
auth_service = AuthService()