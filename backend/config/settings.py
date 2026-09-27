"""
settings.py

Centralized environment configuration.

Every other backend module reads configuration through this file rather
than calling os.environ directly. This keeps secrets out of the code
and gives one place to see every setting the app depends on.

Environment variables can be configured locally through `.env` and
in production through Vercel Environment Variables.
"""

import os
from dotenv import load_dotenv

# Load variables from Backend/.env when running locally.
# In Vercel, environment variables are provided by the platform.
load_dotenv()


def _get_bool(env_var: str, default: bool = False) -> bool:
    """Parse an environment variable into a boolean."""
    value = os.getenv(env_var)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_list(
    env_var: str,
    default: list[str] | None = None,
) -> list[str]:
    """Parse a comma-separated environment variable into a list."""
    value = os.getenv(env_var)

    if value is None:
        return default or []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


class Settings:
    """
    Read-only snapshot of the application's configuration.

    Instantiated once below as `settings` and imported throughout
    the backend.
    """

    def __init__(self) -> None:

        # ---------------------------------------------------------
        # Application mode
        # ---------------------------------------------------------
        self.demo_mode: bool = _get_bool(
            "DEMO_MODE",
            default=True,
        )

        # ---------------------------------------------------------
        # Database
        # ---------------------------------------------------------
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "",
        )

        # ---------------------------------------------------------
        # Frontend URL (For Supabase Auth Redirects)
        # ---------------------------------------------------------
        self.frontend_url: str = os.getenv(
            "FRONTEND_URL",
            "https://green-flora-frontend.vercel.app",
        )

        # ---------------------------------------------------------
        # CORS
        #
        # Allows the deployed Next.js frontend on Vercel to
        # communicate with the FastAPI backend.
        #
        # CORS_ORIGINS can still be overridden through an
        # environment variable.
        #
        # Example:
        # CORS_ORIGINS=http://localhost:3000,https://green-flora-lbwh.vercel.app
        # ---------------------------------------------------------
        self.cors_origins: list[str] = _get_list(
            "CORS_ORIGINS",
            default=[
                "http://localhost:3000",
                "https://green-flora-frontend.vercel.app",
            ],
        )

        # ---------------------------------------------------------
        # Supabase
        # ---------------------------------------------------------
        self.supabase_url: str = os.getenv(
            "SUPABASE_URL",
            "",
        )

        self.supabase_service_key: str = os.getenv(
            "SUPABASE_SERVICE_KEY",
            "",
        )

        self.supabase_anon_key: str = os.getenv(
            "SUPABASE_ANON_KEY",
            "",
        )

        # ---------------------------------------------------------
        # External API keys
        # ---------------------------------------------------------
        self.openweather_api_key: str = os.getenv(
            "OPENWEATHER_API_KEY",
            "",
        )

        self.alibaba_model_studio_key: str = os.getenv(
            "ALIBABA_MODEL_STUDIO_KEY",
            "",
        )

        self.alibaba_oss_key: str = os.getenv(
            "ALIBABA_OSS_KEY",
            "",
        )

        self.alibaba_oss_secret: str = os.getenv(
            "ALIBABA_OSS_SECRET",
            "",
        )

        # ---------------------------------------------------------
        # Gemini
        # Crop Doctor + AI Assistant fallback
        # ---------------------------------------------------------
        self.gemini_api_key: str = os.getenv(
            "GEMINI_API_KEY",
            "",
        )

        # ---------------------------------------------------------
        # OpenAI
        # ---------------------------------------------------------
        self.openai_api_key: str = os.getenv(
            "OPENAI_API_KEY",
            "",
        )

        # ---------------------------------------------------------
        # AI Assistant models
        # ---------------------------------------------------------
        self.ai_main_model: str = os.getenv(
            "AI_MAIN_MODEL",
            "gpt-5.6-luna",
        )

        self.ai_utility_model: str = os.getenv(
            "AI_UTILITY_MODEL",
            "gpt-4o-mini",
        )

        self.ai_transcribe_model: str = os.getenv(
            "AI_TRANSCRIBE_MODEL",
            "gpt-4o-mini-transcribe",
        )

        self.ai_tts_model: str = os.getenv(
            "AI_TTS_MODEL",
            "gpt-4o-mini-tts",
        )

        self.ai_fallback_model: str = os.getenv(
            "AI_FALLBACK_MODEL",
            "gemini-3.6-flash",
        )

        # ---------------------------------------------------------
        # AI timeouts
        # ---------------------------------------------------------
        self.ai_stream_timeout_seconds: float = float(
            os.getenv(
                "AI_STREAM_TIMEOUT_SECONDS",
                "180",
            )
        )

        self.ai_audio_timeout_seconds: float = float(
            os.getenv(
                "AI_AUDIO_TIMEOUT_SECONDS",
                "60",
            )
        )

        # ---------------------------------------------------------
        # General application information
        # ---------------------------------------------------------
        self.app_name: str = "Green Flora API"

        self.environment: str = os.getenv(
            "ENVIRONMENT",
            "development",
        )


# Single shared settings instance.
settings = Settings()