"""``OrganizationMapper`` — ACL between the ``Organization`` aggregate and its row."""

from __future__ import annotations

from apps.organization.domain.entities import Organization
from apps.organization.domain.value_objects import (
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
)
from apps.organization.infrastructure.models import OrganizationModel

__all__ = ["OrganizationMapper"]


class OrganizationMapper:
    """Bidirectional translator between ``Organization`` and ``OrganizationModel``."""

    @staticmethod
    def to_domain(model: OrganizationModel) -> Organization:
        """Reconstruct the aggregate from a persisted row (no re-validation, no events)."""
        return Organization.rehydrate(
            organization_id=OrganizationId.from_uuid(model.id),
            name=OrganizationName(model.name),
            slug=OrganizationSlug(model.slug),
            status=OrganizationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Organization) -> OrganizationModel:
        """Build a brand-new, unsaved ``OrganizationModel`` from an aggregate."""
        return OrganizationModel(**OrganizationMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: Organization) -> dict[str, object]:
        """Flatten an aggregate into ``OrganizationModel`` column values."""
        return {
            "id": entity.id.value,
            "name": entity.name.value,
            "slug": entity.slug.value,
            "status": entity.status.value,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }
