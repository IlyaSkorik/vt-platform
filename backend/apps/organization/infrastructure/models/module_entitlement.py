"""``OrganizationModuleModel`` — persistence for the :class:`ModuleEntitlement` entity.

Persistence only (ARCH-001 §7.2, §14): no invariants, no transitions — the domain
entity owns those. One row per organization per module.

A table rather than a JSON column on the organization row, for two reasons the
domain entity's docstring spells out: an entitlement carries a date and an actor
that an invoice is argued from, and the organization row is already rewritten
wholesale whenever the billing terms change.

``module`` is a free ``CharField`` constrained by a check to the values the domain
enum knows. The check is regenerated with the enum, so a module added next release
is a migration and not a redesign — but a hand-written UPDATE still cannot invent
a tenth module and quietly grant it to everybody.
"""

from __future__ import annotations

from django.db import models

from apps.organization.domain.value_objects import OrganizationModule

from .base import BasePersistenceModel

__all__ = ["ModuleChoices", "OrganizationModuleModel"]


class ModuleChoices(models.TextChoices):
    """The switchable modules (mirrors the domain ``OrganizationModule``).

    Derived from the enum rather than retyped, so a new module is a value in one
    place — the same approach the Results context takes for its award vocabulary.
    """

    COMPETITIONS = OrganizationModule.COMPETITIONS.value, "Фестивали"
    APPLICATIONS = OrganizationModule.APPLICATIONS.value, "Заявки"
    PARTICIPANTS = OrganizationModule.PARTICIPANTS.value, "Участники"
    JURY = OrganizationModule.JURY.value, "Жюри"
    PROGRAMS = OrganizationModule.PROGRAMS.value, "Программа"
    DIPLOMAS = OrganizationModule.DIPLOMAS.value, "Дипломы"
    VOTING = OrganizationModule.VOTING.value, "Зрительское голосование"
    FINANCE = OrganizationModule.FINANCE.value, "Финансы"
    ANALYTICS = OrganizationModule.ANALYTICS.value, "Аналитика"


class OrganizationModuleModel(BasePersistenceModel):
    """Database row for one organization's hold on one module (persistence only)."""

    organization_id = models.UUIDField()
    module = models.CharField(max_length=32, choices=ModuleChoices.choices)
    enabled = models.BooleanField(default=False)
    # When the module was last switched on, and by which platform operator. Kept
    # even while the module is off: "they had the audience vote from March to June"
    # is the question this column exists to answer.
    enabled_at = models.DateTimeField(null=True, blank=True, default=None)
    enabled_by = models.UUIDField(null=True, blank=True, default=None)
    disabled_at = models.DateTimeField(null=True, blank=True, default=None)
    disabled_by = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "organization_module"
        verbose_name = "module entitlement"
        verbose_name_plural = "module entitlements"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The read path: "which modules does this organization hold?", asked on
            # essentially every staff request, so it is served from one index.
            models.Index(fields=["organization_id", "enabled"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(module__in=ModuleChoices.values),
                name="organization_module_valid",
            ),
            # One decision per module per organization. Partial, so a soft-deleted
            # row does not block the module being granted again later.
            models.UniqueConstraint(
                fields=["organization_id", "module"],
                condition=models.Q(deleted_at__isnull=True),
                name="organization_module_unique_per_organization",
            ),
        ]

    def __str__(self) -> str:
        state = "on" if self.enabled else "off"
        return f"{self.module} ({state})"
