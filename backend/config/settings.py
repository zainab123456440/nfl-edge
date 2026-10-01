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


def _get_list(env_var: str, default: list[str] | None = None) -> list[str]:
    """Parse a comma-separated environment variable into a list."""
    value = os.getenv(env_var)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """
    Read-only snapshot of the application's configuration.
    Instantiated once below as `settings` and imported throughout the backend.
    """

    def __init__(self) -> None:

        # ---------------------------------------------------------
        # Application
        # ---------------------------------------------------------
        self.app_name: str = "NFL Edge API"
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.demo_mode: bool = _get_bool("DEMO_MODE", default=True)

        # ---------------------------------------------------------
        # Frontend & CORS
        # ---------------------------------------------------------
        self.frontend_url: str = os.getenv(
            "FRONTEND_URL",
            "http://localhost:3000",
        )

        self.cors_origins: list[str] = _get_list(
            "CORS_ORIGINS",
            default=[
                "http://localhost:3000",
            ],
        )

        # ---------------------------------------------------------
        # Database / Supabase
        # ---------------------------------------------------------
        self.database_url: str = os.getenv("DATABASE_URL", "")

        self.supabase_url: str = os.getenv("SUPABASE_URL", "")
        self.supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")

        # ---------------------------------------------------------
        # OpenAI
        # ---------------------------------------------------------
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

        # Main model used by the AI Assistant
        self.ai_main_model: str = os.getenv(
            "AI_MAIN_MODEL",
            "gpt-4o",                    # ← recommended default
        )

        # Smaller/faster model for lighter tasks (optional)
        self.ai_utility_model: str = os.getenv(
            "AI_UTILITY_MODEL",
            "gpt-4o-mini",
        )

        # ---------------------------------------------------------
        # AI Assistant timeouts & limits
        # ---------------------------------------------------------
        self.ai_stream_timeout_seconds: float = float(
            os.getenv("AI_STREAM_TIMEOUT_SECONDS", "180")
        )

        self.assistant_max_upload_mb: int = int(
            os.getenv("ASSISTANT_MAX_UPLOAD_MB", "20")
        )

        self.assistant_max_tool_rounds: int = int(
            os.getenv("ASSISTANT_MAX_TOOL_ROUNDS", "6")
        )

        self.assistant_max_rows: int = int(
            os.getenv("ASSISTANT_MAX_ROWS", "50")
        )

        self.assistant_file_text_chars: int = int(
            os.getenv("ASSISTANT_FILE_TEXT_CHARS", "60000")
        )


# Single shared settings instance
settings = Settings()