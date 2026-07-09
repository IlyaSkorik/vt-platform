"""``StaffMembershipMapper`` — ACL between ``StaffMembership`` and its row."""

from __future__ import annotations

import uuid

from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import (
    MembershipStatus,
    OrganizationId,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
)
from apps.organization.infrastructure.models import StaffMembershipModel

__all__ = ["StaffMembershipMapper"]


def _opt_user_id(value: uuid.UUID | None) -> StaffUserId | None:
    """Wrap a nullable UUID column into a ``StaffUserId`` or ``None``."""
    return StaffUserId.from_uuid(value) if value is not None else None


class StaffMembershipMapper:
    """Bidirectional translator between ``StaffMembership`` and its model."""

    @staticmethod
    def to_domain(model: StaffMembershipModel) -> StaffMembership:
        """Reconstruct the aggregate from a persisted row (no re-validation, no events)."""
        return StaffMembership.rehydrate(
            membership_id=StaffMembershipId.from_uuid(model.id),
            organization_id=OrganizationId.from_uuid(model.organization_id),
            user_id=StaffUserId.from_uuid(model.user_id),
            role=StaffRole(model.role),
            status=MembershipStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=_opt_user_id(model.created_by),
            updated_by=_opt_user_id(model.updated_by),
            invited_by=_opt_user_id(model.invited_by),
            revoked_by=_opt_user_id(model.revoked_by),
            invited_at=model.invited_at,
            accepted_at=model.accepted_at,
            revoked_at=model.revoked_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: StaffMembership) -> StaffMembershipModel:
        """Build a brand-new, unsaved ``StaffMembershipModel`` from an aggregate."""
        return StaffMembershipModel(**StaffMembershipMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: StaffMembership) -> dict[str, object]:
        """Flatten an aggregate into ``StaffMembershipModel`` column values."""
        return {
            "id": entity.id.value,
            "organization_id": entity.organization_id.value,
            "user_id": entity.user_id.value,
            "role": entity.role.value,
            "status": entity.status.value,
            "created_by": entity.created_by.value if entity.created_by else None,
            "updated_by": entity.updated_by.value if entity.updated_by else None,
            "invited_by": entity.invited_by.value if entity.invited_by else None,
            "revoked_by": entity.revoked_by.value if entity.revoked_by else None,
            "invited_at": entity.invited_at,
            "accepted_at": entity.accepted_at,
            "revoked_at": entity.revoked_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }
