"""Application settings and configuration."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="README Tools", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")

    # Database
    database_path: str = Field(default="data/readme_tools.db", alias="DATABASE_PATH")

    # AI Providers
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")

    # AI Configuration
    default_ai_provider: str = Field(default="openai", alias="DEFAULT_AI_PROVIDER")
    default_model: str = Field(default="gpt-4-turbo", alias="DEFAULT_MODEL")

    # OpenRouter
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_model: str = Field(
        default="anthropic/claude-3-sonnet", alias="OPENROUTER_MODEL"
    )

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama2", alias="OLLAMA_MODEL")

    # Search
    default_search_limit: int = Field(default=10, alias="DEFAULT_SEARCH_LIMIT")
    max_search_limit: int = Field(default=100, alias="MAX_SEARCH_LIMIT")

    # Context Provider
    default_max_context_tokens: int = Field(
        default=4000, alias="DEFAULT_MAX_CONTEXT_TOKENS"
    )
    max_context_tokens: int = Field(default=8000, alias="MAX_CONTEXT_TOKENS")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080", alias="CORS_ORIGINS"
    )

    # Security
    secret_key: str = Field(
        default="change-this-in-production", alias="SECRET_KEY"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def database_path_obj(self) -> Path:
        """Get database path as Path object."""
        return Path(self.database_path)

    def ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        self.database_path_obj.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
