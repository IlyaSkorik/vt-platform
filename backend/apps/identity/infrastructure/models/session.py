"""``UserSessionModel`` — persistence for an authenticated session.

AUTHENTICATION_SESSION owned by USER_ACCOUNT (DIA-001 §4.1, §5.1;
``USER_ACCOUNT ||--o{ AUTHENTICATION_SESSION``). Business-level view of a login
session (DATA-001 §4.1; lifecycle Established → Active → Refreshed → Expired /
Revoked). Persistence only — concurrency, idle/absolute timeout, and remember-me
lifetime rules live in ``SessionPolicy`` and the application layer.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["SessionStatus", "UserSessionModel"]


class SessionStatus(models.TextChoices):
    """Session lifecycle states (DATA-001 §4.1: Established→Active→Refreshed→Expired/Revoked)."""

    ESTABLISHED = "established", "Established"
    ACTIVE = "active", "Active"
    REFRESHED = "refreshed", "Refreshed"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class UserSessionModel(BasePersistenceModel):
    """Database row for one authenticated session (persistence only)."""

    user = models.ForeignKey(
        "identity.UserModel",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    token_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=SessionStatus.choices, default=SessionStatus.ESTABLISHED
    )
    device = models.CharField(max_length=255, null=True, blank=True, default=None)
    ip_address = models.GenericIPAddressField(null=True, blank=True, default=None)
    remember_me = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True, default=None)
    last_activity_at = models.DateTimeField(null=True, blank=True, default=None)
    expires_at = models.DateTimeField(null=True, blank=True, default=None)
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "identity_user_session"
        verbose_name = "session"
        verbose_name_plural = "sessions"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["last_activity_at"]),
            models.Index(fields=["expires_at"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["token_id"], name="identity_session_unique_token_id"),
            models.CheckConstraint(
                condition=models.Q(status__in=SessionStatus.values),
                name="identity_session_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"session {self.id} ({self.status})"
