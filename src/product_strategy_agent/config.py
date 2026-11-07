"""Typed application configuration loaded from environment variables and .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic import Field
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
    qwen_model: str = Field(default="qwen3.8:27b", min_length=1, max_length=250)
    qwen_api_key: SecretStr = SecretStr("")
    qwen_max_output_tokens: int = Field(default=2048, gt=0, le=8192)
    qwen_timeout_seconds: float = Field(default=60, gt=0, le=300)
    qwen_enable_thinking: bool | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; clear the cache in tests after env changes."""

    return Settings()
