"""``PlatformAdministratorModel`` — persistence for the platform-operator grant.

Persistence only (ARCH-001 §7.2, §14). One row per account ever granted platform
access; a revoked grant keeps its row with ``revoked_at`` set, so the record of
who could read across every organization survives the withdrawal.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["PlatformAdministratorModel"]


class PlatformAdministratorModel(BasePersistenceModel):
    """Database row for one platform-administrator grant (persistence only)."""

    # An opaque reference to the Identity account: no foreign key, because the
    # contexts share no tables (ARCH-001 §14).
    user_id = models.UUIDField()
    granted_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "platform_administrator"
        verbose_name = "platform administrator"
        verbose_name_plural = "platform administrators"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["user_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["user_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="platform_unique_administrator_user",
            ),
        ]

    def __str__(self) -> str:
        state = "active" if self.revoked_at is None else "revoked"
        return f"PlatformAdministrator {self.user_id} ({state})"
