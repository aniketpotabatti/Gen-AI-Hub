"""
Application configuration using pydantic-settings.
Reads values from environment variables or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],  # check project root first, then backend/
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────
    app_name: str = "Automated Technical Writer"
    app_version: str = "0.1.0"
    debug: bool = True

    # ── LLM ───────────────────────────────────────────────────────────
    llm_provider: str = "gemini"          # gemini | openai
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.3
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # ── Database ───────────────────────────────────────────────────────
    database_url: str = "sqlite:///./atw.db"  # fallback for quick local dev

    # ── CORS ───────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── Server ─────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
