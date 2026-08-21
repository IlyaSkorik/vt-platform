"""``OrganizationModel`` — persistence for the ``Organization`` aggregate.

Persistence only (ARCH-001 §7.2, §14): no invariants, transitions, or validation
— the domain aggregate owns all of that. One row per organization: the platform's
own (seeded by a data migration) plus every organization the platform operator has
since connected.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from .base import BasePersistenceModel

__all__ = ["BillingModelChoices", "OrganizationModel", "OrganizationStatusChoices"]


class OrganizationStatusChoices(models.TextChoices):
    """Organization lifecycle states (mirrors the domain ``OrganizationStatus``)."""

    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class BillingModelChoices(models.TextChoices):
    """How the platform charges the organization (mirrors the domain ``BillingModel``)."""

    COMMISSION_PERCENT = "COMMISSION_PERCENT", "Commission percent"
    PER_PERFORMANCE_FEE = "PER_PERFORMANCE_FEE", "Per-performance fee"


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
    # The commercial term the organization is connected under. Set by the platform
    # operator, never by the organization's own staff. Exactly one of the two applies
    # — `billing_model` says which — but both are stored, so switching between them
    # does not lose the terms last agreed.
    billing_model = models.CharField(
        max_length=32,
        choices=BillingModelChoices.choices,
        default=BillingModelChoices.COMMISSION_PERCENT,
    )
    # COMMISSION_PERCENT: the share of participation fees owed to the platform.
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    # PER_PERFORMANCE_FEE: the price list, banded by the performance's participant
    # count, as a JSON list of {min_participants, max_participants, amount} rows.
    # A variable-length document that is always read and written whole, so it rides
    # on the row the way the Applications context keeps its aggregates' children.
    performance_fee_tiers = models.JSONField(default=list, blank=True)

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
            models.CheckConstraint(
                condition=models.Q(commission_percent__gte=0, commission_percent__lte=100),
                name="organization_commission_percent_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(billing_model__in=BillingModelChoices.values),
                name="organization_billing_model_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
