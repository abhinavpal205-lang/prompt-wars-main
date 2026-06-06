"""Application settings via pydantic-settings.

This module is the only place that reads environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from the environment / `.env`.

    Every external credential is optional: with everything blank the app runs
    in fully offline stub mode (deterministic form check-in, curated
    reflections, console-logged notifications, voice disabled).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "sqlite:///./data/sahaay.db"
    fernet_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def openai_configured(self) -> bool:
        """Whether OpenAI-backed features (voice, AI signals) can be used."""
        return bool(self.openai_api_key)

    @property
    def smtp_configured(self) -> bool:
        """Whether real email delivery is configured (else console stub)."""
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
