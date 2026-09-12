"""``ModuleEntitlementMapper`` — ACL between ``ModuleEntitlement`` and its row."""

from __future__ import annotations

import uuid

from apps.organization.domain.entities import ModuleEntitlement
from apps.organization.domain.value_objects import (
    ModuleEntitlementId,
    OrganizationId,
    OrganizationModule,
    StaffUserId,
)
from apps.organization.infrastructure.models import OrganizationModuleModel

__all__ = ["ModuleEntitlementMapper"]


def _opt_user_id(value: uuid.UUID | None) -> StaffUserId | None:
    """Wrap a nullable UUID column into a ``StaffUserId`` or ``None``."""
    return StaffUserId.from_uuid(value) if value is not None else None


class ModuleEntitlementMapper:
    """Bidirectional translator between ``ModuleEntitlement`` and its model."""

    @staticmethod
    def to_domain(model: OrganizationModuleModel) -> ModuleEntitlement:
        """Reconstruct the entity from a persisted row (no re-validation, no events)."""
        return ModuleEntitlement.rehydrate(
            entitlement_id=ModuleEntitlementId.from_uuid(model.id),
            organization_id=OrganizationId.from_uuid(model.organization_id),
            module=OrganizationModule(model.module),
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
            enabled_at=model.enabled_at,
            enabled_by=_opt_user_id(model.enabled_by),
            disabled_at=model.disabled_at,
            disabled_by=_opt_user_id(model.disabled_by),
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: ModuleEntitlement) -> OrganizationModuleModel:
        """Build a brand-new, unsaved ``OrganizationModuleModel`` from an entity."""
        return OrganizationModuleModel(**ModuleEntitlementMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: ModuleEntitlement) -> dict[str, object]:
        """Flatten an entity into ``OrganizationModuleModel`` column values."""
        return {
            "id": entity.id.value,
            "organization_id": entity.organization_id.value,
            "module": entity.module.value,
            "enabled": entity.enabled,
            "enabled_at": entity.enabled_at,
            "enabled_by": entity.enabled_by.value if entity.enabled_by else None,
            "disabled_at": entity.disabled_at,
            "disabled_by": entity.disabled_by.value if entity.disabled_by else None,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }
