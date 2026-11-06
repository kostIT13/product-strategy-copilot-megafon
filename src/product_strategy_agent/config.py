"""Typed application configuration loaded from environment variables and .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by CLI, MCP, and application services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    projects_dir: Path = Path("projects")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://product_strategy:local-dev-change-this@localhost:5432/product_strategy"
    )

    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen3.8:27b"
    qwen_api_key: SecretStr = SecretStr("")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; clear the cache in tests after env changes."""

    return Settings()
