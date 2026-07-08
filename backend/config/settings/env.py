"""Strongly-typed configuration via Pydantic Settings.

This is the single source of environment configuration for the VT Platform
backend. Per the platform standard we use **Pydantic Settings** (not
django-environ): configuration is declared once, validated, and strongly typed,
then consumed by the Django settings modules in this package.

12-factor: all values come from environment variables (or a local ``.env`` file
for development). Secrets are never committed (ARCH-001 §16.3).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings (ARCH-001 §9)."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    db: str = "vt_platform"
    user: str = "vt_platform"
    password: str = "vt_platform"
    host: str = "localhost"
    port: int = 5432


class JWTSettings(BaseSettings):
    """JWT authentication settings (ARCH-001 §11, API-000 §17)."""

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")

    # Short-lived access token; rotating refresh token (in minutes / days).
    access_token_lifetime_minutes: int = 15
    refresh_token_lifetime_days: int = 14
    rotate_refresh_tokens: bool = True
    blacklist_after_rotation: bool = True


class EmailSettings(BaseSettings):
    """Transactional email / SMTP settings (ARCH-001 §17.3, IDN-002).

    Drives Django's email backend. The development stack points these at the
    Mailhog SMTP sink (``mailhog:1025``, no TLS); production supplies a real
    provider's host, port, credentials, and TLS via the environment.
    """

    model_config = SettingsConfigDict(env_prefix="EMAIL_", extra="ignore")

    backend: str = "django.core.mail.backends.smtp.EmailBackend"
    host: str = "localhost"
    port: int = 1025
    host_user: str = ""
    host_password: str = ""
    use_tls: bool = False
    use_ssl: bool = False
    timeout: int = 10
    # Envelope sender for transactional mail (IDN-002 verification, resets).
    default_from: str = "no-reply@vzlyot-talantov.ru"


class Settings(BaseSettings):
    """Root application settings.

    Instances are built from environment variables. Nested settings groups
    (database, JWT) are composed explicitly so each reads its own env prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core Django ---
    secret_key: str = Field(
        default="insecure-dev-secret-key-change-me",
        alias="DJANGO_SECRET_KEY",
    )
    debug: bool = Field(default=False, alias="DJANGO_DEBUG")
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost"],
        alias="DJANGO_ALLOWED_HOSTS",
    )

    # --- Localization (ARCH-001: timezone UTC, language ru) ---
    time_zone: str = Field(default="UTC", alias="DJANGO_TIME_ZONE")
    language_code: str = Field(default="ru", alias="DJANGO_LANGUAGE_CODE")

    # --- Networking / CORS (API-000 §26, ARCH-001 §10.4) ---
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="DJANGO_CORS_ALLOWED_ORIGINS",
    )

    # Public base URL of the web client, used to build user-facing links that the
    # backend emails (e.g. the email-verification link, IDN-002). No trailing slash.
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_BASE_URL",
    )

    # --- Redis / Celery (ARCH-001 §6.1, §7.5) ---
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",  # type: ignore[assignment]
        alias="REDIS_URL",
    )
    celery_broker_url: RedisDsn = Field(
        default="redis://localhost:6379/1",  # type: ignore[assignment]
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: RedisDsn = Field(
        default="redis://localhost:6379/2",  # type: ignore[assignment]
        alias="CELERY_RESULT_BACKEND",
    )

    # --- Composed groups ---
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)

    @field_validator("allowed_hosts", "cors_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allow comma-separated env strings for list fields."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated settings instance."""
    return Settings()
