"""``UserModel`` — persistence representation of the ``User`` aggregate root.

Maps every field of the ``apps.identity.domain.entities.User`` aggregate to a
column (USER_ACCOUNT — DIA-001 §4.1, §5.1). This is a **persistence model only**:
it holds no invariants, transitions, or validation — the domain aggregate owns
all of that. The mapper/repository projects a ``User`` onto these columns and
rehydrates it back.

Uniqueness of email/phone is enforced only among **active** (non-soft-deleted)
rows via partial unique constraints, honouring "one verified email maps to at
most one active account" (DATA-001 §4.1) while still allowing an address to be
reused after an account is erased.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["UserModel"]


class UserModel(BasePersistenceModel):
    """Database row for a user account (persistence only — no business logic)."""

    # Contact details. ``email`` is stored normalized (lowercased) by the domain
    # ``Email`` value object before it ever reaches this column.
    email = models.EmailField(max_length=320)
    phone = models.CharField(max_length=16, null=True, blank=True, default=None)

    # Name (``FullName`` value object: given / family / optional patronymic).
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True, default=None)

    # Preferences.
    locale = models.CharField(max_length=10)
    timezone = models.CharField(max_length=64)

    # Credential digest (``PasswordHash`` value object: opaque encoded hash + algo).
    password_algorithm = models.CharField(max_length=32)
    password_hash = models.CharField(max_length=255)

    # Currently-accepted consent-text version (``ConsentVersion``), if any.
    consent_version = models.CharField(max_length=64, null=True, blank=True, default=None)

    # Verification / lock state (all authoritative on the aggregate).
    email_verified_at = models.DateTimeField(null=True, blank=True, default=None)
    phone_verified_at = models.DateTimeField(null=True, blank=True, default=None)
    locked_until = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "identity_user"
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(deleted_at__isnull=True),
                name="identity_user_unique_active_email",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(deleted_at__isnull=True, phone__isnull=False),
                name="identity_user_unique_active_phone",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.id})"
