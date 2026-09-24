"""Application settings, loaded from environment variables.

Kept deliberately small for the prototype: see docs/architecture.md §3 for
what is real vs. simulated. No enterprise credentials belong here.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Resolvyn"
    environment: str = "development"
    database_url: str = "sqlite:///./data/resolvyn.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Optional: if unset, the app falls back to deterministic mock outputs
    # instead of calling a real LLM (project.md §87, "Optional AI integration").
    llm_api_key: str | None = None
    llm_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
