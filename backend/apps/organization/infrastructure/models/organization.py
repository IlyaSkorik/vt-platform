"""``OrganizationModel`` — persistence for the singleton ``Organization`` aggregate.

Persistence only (ARCH-001 §7.2, §14): no invariants, transitions, or validation
— the domain aggregate owns all of that. There is exactly one active row (seeded
by a data migration); public creation is forbidden at the application layer.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["OrganizationModel", "OrganizationStatusChoices"]


class OrganizationStatusChoices(models.TextChoices):
    """Organization lifecycle states (mirrors the domain ``OrganizationStatus``)."""

    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class OrganizationModel(BasePersistenceModel):
    """Database row for the organization (persistence only — no business logic)."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    status = models.CharField(
        max_length=16,
        choices=OrganizationStatusChoices.choices,
        default=OrganizationStatusChoices.ACTIVE,
    )
    # Optional public contact & legal profile (owned by the domain OrganizationProfile
    # value object; nullable because a freshly seeded organization has none set).
    phone = models.CharField(max_length=200, null=True, blank=True, default=None)
    email = models.CharField(max_length=200, null=True, blank=True, default=None)
    website = models.CharField(max_length=200, null=True, blank=True, default=None)
    address = models.CharField(max_length=500, null=True, blank=True, default=None)
    logo = models.CharField(max_length=200, null=True, blank=True, default=None)
    vk = models.CharField(max_length=200, null=True, blank=True, default=None)
    instagram = models.CharField(max_length=200, null=True, blank=True, default=None)
    telegram = models.CharField(max_length=200, null=True, blank=True, default=None)
    legal_information = models.TextField(max_length=5000, null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "organization_organization"
        verbose_name = "organization"
        verbose_name_plural = "organizations"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="organization_unique_active_slug",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=OrganizationStatusChoices.values),
                name="organization_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
