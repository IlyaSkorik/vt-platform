"""``DjangoModuleEntitlementRepository`` — ORM adapter for ``ModuleEntitlement``."""

from __future__ import annotations

from collections.abc import Sequence

from django.db import DatabaseError

from apps.organization.domain.entities import ModuleEntitlement
from apps.organization.domain.value_objects import OrganizationId, OrganizationModule
from apps.organization.infrastructure.mappers import ModuleEntitlementMapper
from apps.organization.infrastructure.models import OrganizationModuleModel

from ._upsert import optimistic_upsert
from .exceptions import PersistenceError

__all__ = ["DjangoModuleEntitlementRepository"]


class DjangoModuleEntitlementRepository:
    """Django ORM adapter implementing the ``ModuleEntitlementRepository`` port."""

    def find(self, *, organization_id: OrganizationId, module: OrganizationModule) -> ModuleEntitlement | None:
        """Return the organization's entitlement to ``module``, or ``None`` if never decided."""
        try:
            model = OrganizationModuleModel.objects.get(
                organization_id=organization_id.value,
                module=module.value,
                deleted_at__isnull=True,
            )
        except OrganizationModuleModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load entitlement to {module.value}.") from exc
        return ModuleEntitlementMapper.to_domain(model)

    def list_by_organization(self, organization_id: OrganizationId) -> Sequence[ModuleEntitlement]:
        """Return every decided entitlement of the organization, in module order."""
        try:
            models = list(
                OrganizationModuleModel.objects.filter(
                    organization_id=organization_id.value,
                    deleted_at__isnull=True,
                ).order_by("module")
            )
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list module entitlements.") from exc
        return [ModuleEntitlementMapper.to_domain(model) for model in models]

    def enabled_modules(self, organization_id: OrganizationId) -> frozenset[OrganizationModule]:
        """Return only the modules the organization currently holds.

        The hot path — consulted on staff requests and on ``/users/me`` — so it
        reads the two columns it needs from the covering index and rehydrates no
        entity at all.
        """
        try:
            rows = OrganizationModuleModel.objects.filter(
                organization_id=organization_id.value,
                enabled=True,
                deleted_at__isnull=True,
            ).values_list("module", flat=True)
            return frozenset(OrganizationModule(value) for value in rows)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to read enabled modules.") from exc

    def save(self, entitlement: ModuleEntitlement) -> None:
        """Persist ``entitlement`` (insert or update), honouring its version."""
        model = ModuleEntitlementMapper.to_model(entitlement)
        optimistic_upsert(
            model_cls=OrganizationModuleModel,
            pk=entitlement.id.value,
            version=entitlement.version,
            columns=_column_values(model),
        )


def _column_values(model: OrganizationModuleModel) -> dict[str, object]:
    """Flatten a mapped model into its concrete column values."""
    return {field.attname: getattr(model, field.attname) for field in OrganizationModuleModel._meta.concrete_fields}
