from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2 settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_ENV: str = "dev"

    # Database
    DATABASE_URL: str = "sqlite:///./data/crm_saas.sqlite"

    # JWT
    JWT_SECRET: str = "ChangeThisToLongRandomSecret"
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 10080  # 7 days

    # OTP
    OTP_TTL_SECONDS: int = 900  # 15 min

    # OpenAI (optional)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-5-mini"

    # Webhook
    WEBHOOK_VERIFY_TOKEN: str = "change-me-verify-token"

    # Superadmin bootstrap
    SUPERADMIN_EMAIL: str = "admin@example.com"
    SUPERADMIN_PASSWORD: str = "ChangeThisPassword123!"


settings = Settings()


# Backward-compatible helpers (avoid breaking existing imports)
def get_database_url() -> str:
    return settings.DATABASE_URL


@property
def database_url(self) -> str:
    return self.DATABASE_URL


# If any old code uses settings.database_url, this makes it work
Settings.database_url = database_url  # type: ignore
