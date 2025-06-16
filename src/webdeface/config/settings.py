"""Pydantic settings models for configuration management."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from .types import ConfigError


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    url: str = "sqlite:///./data/webdeface.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v:
            raise ValueError("Database URL cannot be empty")
        return v


class QdrantSettings(BaseModel):
    """Qdrant vector database configuration."""

    url: str = "http://localhost:6333"
    collection_name: str = "webdeface"
    vector_size: int = 384
    distance: str = "Cosine"

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v:
            raise ValueError("Qdrant URL cannot be empty")
        return v

    @field_validator("vector_size")
    @classmethod
    def validate_vector_size(cls, v):
        if v <= 0:
            raise ValueError("Vector size must be positive")
        return v


class SlackSettings(BaseModel):
    """Slack integration configuration."""

    bot_token: SecretStr = Field(default="")
    app_token: SecretStr = Field(default="")
    signing_secret: SecretStr = Field(default="")
    allowed_users: list[str] = Field(default_factory=list)

    @field_validator("bot_token", "app_token", "signing_secret")
    @classmethod
    def validate_tokens(cls, v):
        # Allow empty tokens in debug/test mode, but validate in production
        if v and not v.get_secret_value():
            raise ValueError("Slack tokens cannot be empty")
        return v


class ClaudeSettings(BaseModel):
    """Claude AI configuration."""

    api_key: SecretStr = Field(default="")
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4000
    temperature: float = 0.1

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        # Allow empty API key in debug/test mode, but validate in production
        if v and not v.get_secret_value():
            raise ValueError("Claude API key cannot be empty")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        if v <= 0 or v > 100000:
            raise ValueError("Max tokens must be between 1 and 100000")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if v < 0.0 or v > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v


class ScrapingSettings(BaseModel):
    """Web scraping configuration."""

    default_timeout: int = 10000  # milliseconds
    max_retries: int = 3
    max_depth: int = 3
    user_agents: list[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (compatible; WebDefaceMonitor/1.0)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        ]
    )

    @field_validator("default_timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, v):
        if v < 0:
            raise ValueError("Max retries cannot be negative")
        return v

    @field_validator("max_depth")
    @classmethod
    def validate_depth(cls, v):
        if v <= 0:
            raise ValueError("Max depth must be positive")
        return v


class AppSettings(BaseSettings):
    """Main application settings."""

    # Core application settings
    debug: bool = False
    log_level: str = "INFO"
    keep_scans: int = 20
    __version__: str = "0.1.0"

    # API authentication
    api_tokens: list[str] = Field(default_factory=lambda: ["dev-token-12345"])

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    slack: SlackSettings = Field(default_factory=SlackSettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False
        # Allow extra fields for flexibility
        extra = "allow"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("keep_scans")
    @classmethod
    def validate_keep_scans(cls, v):
        if v <= 0:
            raise ValueError("Keep scans must be positive")
        return v


# Global settings instance
_settings: Optional[AppSettings] = None


@lru_cache
def get_settings() -> AppSettings:
    """Get the application settings instance."""
    global _settings

    if _settings is None:
        try:
            _settings = AppSettings()
        except Exception as e:
            raise ConfigError(f"Failed to load settings: {str(e)}") from e

    return _settings


def reload_settings() -> AppSettings:
    """Force reload of settings (useful for testing)."""
    global _settings
    _settings = None
    get_settings.cache_clear()
    return get_settings()


def update_settings(**kwargs) -> AppSettings:
    """Update settings with new values."""
    global _settings

    if _settings is None:
        _settings = get_settings()

    # Create new settings instance with updated values
    current_dict = _settings.dict()
    current_dict.update(kwargs)

    try:
        _settings = AppSettings(**current_dict)
        get_settings.cache_clear()
        return _settings
    except Exception as e:
        raise ConfigError(f"Failed to update settings: {str(e)}") from e


def validate_settings(settings: AppSettings) -> None:
    """Validate settings for common configuration issues."""
    # Check for required environment variables in production
    if not settings.debug:
        required_secrets = [
            ("Slack bot token", settings.slack.bot_token),
            ("Slack app token", settings.slack.app_token),
            ("Slack signing secret", settings.slack.signing_secret),
            ("Claude API key", settings.claude.api_key),
        ]

        for name, secret in required_secrets:
            if not secret or not secret.get_secret_value():
                raise ConfigError(f"{name} must be configured in production mode")

    # Validate database path for SQLite
    if settings.database.url.startswith("sqlite:"):
        db_path = settings.database.url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError as e:
                raise ConfigError(f"Cannot create database directory: {str(e)}") from e
