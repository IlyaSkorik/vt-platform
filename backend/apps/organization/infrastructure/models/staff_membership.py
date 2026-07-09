"""``StaffMembershipModel`` — persistence for the ``StaffMembership`` aggregate.

Persistence only (ARCH-001 §7.2, §14). ``organization_id`` and ``user_id`` are
plain UUID columns, **not** foreign keys: the user lives in another bounded
context (Identity) and must never be joined across the boundary. The partial
unique constraint enforces "at most one ACTIVE membership per user per
organization"; the audit columns (created/updated/invited/revoked by & at)
support a future audit log.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["MembershipStatusChoices", "StaffMembershipModel", "StaffRoleChoices"]


class StaffRoleChoices(models.TextChoices):
    """Staff roles (mirrors the domain ``StaffRole``)."""

    OWNER = "OWNER", "Owner"
    DIRECTOR = "DIRECTOR", "Director"
    FINANCE = "FINANCE", "Finance"
    COMPETITION_MANAGER = "COMPETITION_MANAGER", "Competition manager"
    CONTENT_MANAGER = "CONTENT_MANAGER", "Content manager"
    MODERATOR = "MODERATOR", "Moderator"
    SUPPORT = "SUPPORT", "Support"


class MembershipStatusChoices(models.TextChoices):
    """Membership lifecycle states (mirrors the domain ``MembershipStatus``)."""

    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    REVOKED = "REVOKED", "Revoked"


class StaffMembershipModel(BasePersistenceModel):
    """Database row for a staff membership (persistence only — no business logic)."""

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    role = models.CharField(max_length=32, choices=StaffRoleChoices.choices)
    status = models.CharField(
        max_length=16,
        choices=MembershipStatusChoices.choices,
        default=MembershipStatusChoices.PENDING,
    )

    # Audit trail (all nullable UUID/timestamp columns — future audit log).
    created_by = models.UUIDField(null=True, blank=True, default=None)
    updated_by = models.UUIDField(null=True, blank=True, default=None)
    invited_by = models.UUIDField(null=True, blank=True, default=None)
    revoked_by = models.UUIDField(null=True, blank=True, default=None)
    invited_at = models.DateTimeField(null=True, blank=True, default=None)
    accepted_at = models.DateTimeField(null=True, blank=True, default=None)
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "organization_staff_membership"
        verbose_name = "staff membership"
        verbose_name_plural = "staff memberships"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organization_id", "user_id"]),
            models.Index(fields=["organization_id", "status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["organization_id", "user_id"],
                condition=models.Q(status="ACTIVE", deleted_at__isnull=True),
                name="organization_unique_active_membership",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=MembershipStatusChoices.values),
                name="organization_membership_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=StaffRoleChoices.values),
                name="organization_membership_role_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"membership {self.id} ({self.role}/{self.status})"
