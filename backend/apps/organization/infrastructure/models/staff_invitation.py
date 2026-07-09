"""``StaffInvitationModel`` — persistence for the ``StaffInvitation`` aggregate.

Persistence only (ARCH-001 §7.2, §14). The ``token_hash`` column stores the
SHA-256 digest of the invitation secret — the raw token is emailed and **never**
persisted (same philosophy as password storage). ``organization_id`` and
``invited_by`` are plain UUID columns, not foreign keys (cross-context refs).
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .staff_membership import StaffRoleChoices

__all__ = ["StaffInvitationModel"]


class StaffInvitationModel(BasePersistenceModel):
    """Database row for a staff invitation (persistence only — no business logic)."""

    organization_id = models.UUIDField()
    email = models.EmailField(max_length=320)
    role = models.CharField(max_length=32, choices=StaffRoleChoices.choices)
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    invited_by = models.UUIDField()
    accepted_at = models.DateTimeField(null=True, blank=True, default=None)
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "organization_staff_invitation"
        verbose_name = "staff invitation"
        verbose_name_plural = "staff invitations"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organization_id", "email"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["token_hash"],
                name="organization_invitation_unique_token_hash",
            ),
            models.UniqueConstraint(
                fields=["organization_id", "email"],
                condition=models.Q(
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                    deleted_at__isnull=True,
                ),
                name="organization_unique_pending_invitation",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=StaffRoleChoices.values),
                name="organization_invitation_role_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"invitation {self.id} ({self.email}/{self.role})"
