"""Typed application configuration loaded from environment variables and .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by CLI, MCP, and application services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    projects_dir: Path = Path("projects")

    # QWEN_* aliases allow existing local environments to migrate gradually.
    llm_base_url: str = Field(default="https://provider.example/v1", validation_alias=AliasChoices("LLM_BASE_URL", "QWEN_BASE_URL"))
    llm_model: str = Field(default="Qwen3.8-27B", min_length=1, max_length=250,
                           validation_alias=AliasChoices("LLM_MODEL", "QWEN_MODEL"))
    llm_api_key: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("LLM_API_KEY", "QWEN_API_KEY"))
    llm_max_output_tokens: int = Field(default=2048, gt=0, le=8192,
                                      validation_alias=AliasChoices("LLM_MAX_OUTPUT_TOKENS", "QWEN_MAX_OUTPUT_TOKENS"))
    llm_timeout_seconds: float = Field(default=60, gt=0, le=300,
                                       validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "QWEN_TIMEOUT_SECONDS"))
    llm_extra_body: dict = Field(default_factory=dict)



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; clear the cache in tests after env changes."""

    return Settings()
