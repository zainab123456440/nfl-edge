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

    Instantiated once below as `settings` and imported
    throughout the backend.
    """

    def __init__(self) -> None:

        # ---------------------------------------------------------
        # Application
        # ---------------------------------------------------------
        self.app_name: str = "NFL Edge API"

        self.environment: str = os.getenv(
            "ENVIRONMENT",
            "development",
        )

        self.demo_mode: bool = _get_bool(
            "DEMO_MODE",
            default=True,
        )

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
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "",
        )

        self.supabase_url: str = os.getenv(
            "SUPABASE_URL",
            "",
        )

        self.supabase_service_key: str = os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY",
            "",
        )

        self.supabase_anon_key: str = os.getenv(
            "SUPABASE_ANON_KEY",
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
        # AI Assistant - Light Route
        # ---------------------------------------------------------
        # Normal questions, simple database lookups,
        # small tool calls, and quick NFL queries.

        self.ai_light_model: str = os.getenv(
            "AI_LIGHT_MODEL",
            "gpt-5-mini",
        )

        self.ai_light_effort: str = os.getenv(
            "AI_LIGHT_EFFORT",
            "low",
        )

        self.ai_light_max_output_tokens: int = int(
            os.getenv(
                "AI_LIGHT_MAX_OUTPUT_TOKENS",
                "16000",
            )
        )

        # ---------------------------------------------------------
        # AI Assistant - Heavy Route
        # ---------------------------------------------------------
        # Large CSVs, uploaded files, large pasted data,
        # lineup generation, complex analysis, and file generation.

        self.ai_heavy_model: str = os.getenv(
            "AI_HEAVY_MODEL",
            "gpt-5.1",
        )

        self.ai_heavy_effort: str = os.getenv(
            "AI_HEAVY_EFFORT",
            "medium",
        )

        # Large output allowance for complex analysis and
        # generated lineup/file responses.
        self.ai_heavy_max_output_tokens: int = int(
            os.getenv(
                "AI_HEAVY_MAX_OUTPUT_TOKENS",
                "64000",
            )
        )

        # Maximum characters in a large user message.
        self.ai_heavy_message_chars: int = int(
            os.getenv(
                "AI_HEAVY_MESSAGE_CHARS",
                "100000",
            )
        )

        # Maximum extracted text allowed from a heavy file.
        #
        # This is deliberately much larger than the old 60,000
        # character limit so KB-sized CSVs with many rows are not
        # unnecessarily truncated.
        self.ai_heavy_file_chars: int = int(
            os.getenv(
                "AI_HEAVY_FILE_CHARS",
                "5000000",
            )
        )

        # ---------------------------------------------------------
        # Legacy / General AI settings
        # ---------------------------------------------------------
        # Kept for compatibility with existing backend code.

        self.ai_main_model: str = os.getenv(
            "AI_MAIN_MODEL",
            "gpt-5-mini",
        )

        self.ai_utility_model: str = os.getenv(
            "AI_UTILITY_MODEL",
            "gpt-5-mini",
        )

        # ---------------------------------------------------------
        # AI Assistant execution
        # ---------------------------------------------------------
        # Maximum time the backend allows the AI operation to run.
        #
        # This does not override Vercel's own function duration
        # limits. It only controls the application's timeout.

        self.ai_stream_timeout_seconds: float = float(
            os.getenv(
                "AI_STREAM_TIMEOUT_SECONDS",
                "300",
            )
        )

        # ---------------------------------------------------------
        # File upload limits
        # ---------------------------------------------------------
        # Maximum physical upload size accepted by the application.
        #
        # IMPORTANT:
        # Vercel Functions have their own request-body limit, so
        # this setting cannot bypass Vercel's platform limit.
        # For direct local/FastAPI usage, 100 MB is reasonable.

        self.assistant_max_upload_mb: int = int(
            os.getenv(
                "ASSISTANT_MAX_UPLOAD_MB",
                "100",
            )
        )

        # ---------------------------------------------------------
        # Tool execution
        # ---------------------------------------------------------

        self.assistant_max_tool_rounds: int = int(
            os.getenv(
                "ASSISTANT_MAX_TOOL_ROUNDS",
                "8",
            )
        )

        # Maximum number of database rows returned by normal
        # database tools. This is separate from uploaded files.
        self.assistant_max_rows: int = int(
            os.getenv(
                "ASSISTANT_MAX_ROWS",
                "100",
            )
        )

        # General file text allowance.
        #
        # Heavy files use ai_heavy_file_chars above.
        self.assistant_file_text_chars: int = int(
            os.getenv(
                "ASSISTANT_FILE_TEXT_CHARS",
                "5000000",
            )
        )


# Single shared settings instance
settings = Settings()