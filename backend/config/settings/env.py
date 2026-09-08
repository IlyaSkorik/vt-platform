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


def _group_config(prefix: str) -> SettingsConfigDict:
    """Config for a nested settings group, including the ``.env`` file.

    The ``env_file`` is the part worth spelling out. A nested group does not inherit the
    root's config, so without it a group reads process environment only - and that failure
    is invisible under Docker Compose, where ``env_file:`` injects everything as real
    environment variables. Run the backend on the host instead and ``EMAIL_HOST`` in
    ``.env`` is silently ignored while the defaults quietly stand in for it.
    """
    return SettingsConfigDict(
        env_prefix=prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings (ARCH-001 §9)."""

    model_config = _group_config("POSTGRES_")

    db: str = "vt_platform"
    user: str = "vt_platform"
    password: str = "vt_platform"
    host: str = "localhost"
    port: int = 5432


class JWTSettings(BaseSettings):
    """JWT authentication settings (ARCH-001 §11, API-000 §17)."""

    model_config = _group_config("JWT_")

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

    model_config = _group_config("EMAIL_")

    backend: str = "django.core.mail.backends.smtp.EmailBackend"
    host: str = "localhost"
    port: int = 1025
    host_user: str = ""
    host_password: str = ""
    use_tls: bool = False
    use_ssl: bool = False
    timeout: int = 10
    # Envelope sender for mail somebody is waiting on: verification links, password
    # resets, staff invitations, payment deadlines (IDN-002).
    default_from: str = "no-reply@vzlettalantov.by"
    # Envelope sender for notices produced in batches: submission receipts, an
    # organizer's review outcomes, the auto-cancellation sweep.
    #
    # A second mailbox is the cheapest way to buy headroom, because the provider counts
    # its 30-a-minute allowance per mailbox: a registration rush or an organizer working
    # through eighty applications can no longer delay a password reset. Empty means "use
    # ``default_from``", which is a single-mailbox deployment and still correct.
    bulk_from: str = ""

    # --- The provider's mailbox quotas (OPS-009) ---------------------------
    #
    # These are contractual limits on the hosting provider's mail servers, not tuning
    # knobs: exceeding them gets outbound mail throttled or refused. They are settings
    # rather than constants because a different provider (or tariff) has different numbers.
    #
    # 30 outgoing messages per minute per mailbox. Zero disables the limiter, which is what
    # the test suite runs on - the quota has its own focused tests.
    rate_limit_per_minute: int = 30
    # 50 recipients per message, counting To + Cc + Bcc together.
    max_recipients: int = 50
    # 100 MB per message. Refused locally rather than spent on a rejection.
    max_bytes: int = 100 * 1024 * 1024


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

    # --- OpenAPI docs access (API-000 §26) ---
    #
    # The schema is a complete map of the API: every path, every parameter, every field
    # name and enum value. That is exactly the reconnaissance an attacker would otherwise
    # have to assemble by hand, so outside development the three doc routes sit behind
    # HTTP Basic auth (config/api_docs.py).
    #
    # These are shared credentials for a read-only reference, not user accounts — one pair
    # per deployment, kept in the secret store (OPS-008 §9). Leave them empty in a
    # deployment and the routes are not served at all: unset must fail closed, or a
    # forgotten variable silently publishes the whole contract.
    api_docs_user: str = Field(default="", alias="API_DOCS_USER")
    api_docs_password: str = Field(default="", alias="API_DOCS_PASSWORD")

    # --- Whole-site gate for a deployment that is not public (OPS-001 §10) ---
    #
    # Set on the staging stand, which is a complete copy of the site and must not be
    # reachable by a crawler or by anyone who guesses the subdomain. Both empty in
    # production, where the site *is* public — and empty removes the middleware from the
    # chain entirely (config/middleware.py), so the normal case costs nothing.
    #
    # Note the default is the opposite of the docs gate above: there an unset variable
    # must fail closed, because it would otherwise publish the whole contract. Here unset
    # describes production, so it opens.
    site_gate_user: str = Field(default="", alias="SITE_GATE_USER")
    site_gate_password: str = Field(default="", alias="SITE_GATE_PASSWORD")

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

    # Absolute path to the built SPA's ``index.html``. Set it when Django serves
    # the bundle, so browser routes are answered with their ``<head>`` already
    # filled in — link previews in Telegram/VK are built by crawlers that never
    # run the app's JavaScript. Empty (the default, and the case while Vite serves
    # the SPA) leaves the catch-all unmounted entirely.
    spa_index_path: str = Field(
        default="",
        alias="SPA_INDEX_PATH",
    )

    # Public base URL the diploma QR code points at: the printed link is
    # ``<base>/verify/<verificationToken>``. Empty means "use frontend_base_url" —
    # set it only when authenticity checks live on their own domain. No trailing slash.
    diploma_verification_base_url: str = Field(
        default="",
        alias="DIPLOMA_VERIFICATION_BASE_URL",
    )

    # Hours an applicant has to attach a payment receipt after submitting before the
    # order is auto-cancelled. Lower it (e.g. to a fraction of an hour) to exercise the
    # auto-cancellation flow locally without waiting the production default.
    application_payment_window_hours: float = Field(
        default=48.0,
        gt=0,
        alias="APPLICATION_PAYMENT_WINDOW_HOURS",
    )

    # How often (minutes) the Celery Beat sweep checks for overdue unpaid orders to
    # auto-cancel. Lower it alongside the window to test the flow quickly.
    application_payment_sweep_minutes: float = Field(
        default=15.0,
        gt=0,
        alias="APPLICATION_PAYMENT_SWEEP_MINUTES",
    )

    # How often (minutes) the Celery Beat sweep looks for orders edited after they were
    # submitted, to tell the organizer what changed.
    application_revision_digest_minutes: float = Field(
        default=15.0,
        gt=0,
        alias="APPLICATION_REVISION_DIGEST_MINUTES",
    )

    # How long an order must go unedited before its edits are reported. This is what
    # turns one editing session into one letter instead of one letter per pause; raise
    # it if organizers still see an edit split across two notices.
    application_revision_quiet_minutes: float = Field(
        default=5.0,
        gt=0,
        alias="APPLICATION_REVISION_QUIET_MINUTES",
    )

    # --- Object storage for uploads and generated documents ---
    #
    # Set ``S3_BUCKET`` and the platform stores every upload, diploma and archive in that
    # bucket instead of the local filesystem; leave it empty and nothing changes, which is
    # what local work and the test suite run on.
    #
    # The bucket is expected to be **public-read**: references are stable URLs a browser
    # and a CDN can cache, so a poster on a landing page is fetched once rather than on
    # every render. Confidentiality comes from the key being unguessable, not from the
    # bucket being closed - see ``apps/diplomas/infrastructure/pdf/workspace.py``.
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_region: str = Field(default="", alias="S3_REGION")
    #: Required for anything that is not AWS itself (Yandex, Selectel, VK, MinIO).
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="", alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="", alias="S3_SECRET_ACCESS_KEY")
    #: A CDN or vanity host in front of the bucket, if there is one. No scheme, no slash.
    s3_custom_domain: str = Field(default="", alias="S3_CUSTOM_DOMAIN")
    #: Optional key prefix, so one bucket can carry several environments.
    s3_location: str = Field(default="", alias="S3_LOCATION")
    #: Where a host keeps local copies of uploaded diploma fonts. reportlab embeds a font by
    #: opening a file, so a font in the bucket has to be on local disk before it can be drawn.
    #: Empty means the system temp directory, which is right for a single host; point it at a
    #: shared volume so a container fleet fetches each font once rather than once per container.
    diploma_font_cache_dir: str = Field(default="", alias="DIPLOMA_FONT_CACHE_DIR")

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
