"""``StaffInvitationMapper`` — ACL between ``StaffInvitation`` and its row."""

from __future__ import annotations

from apps.organization.domain.entities import StaffInvitation
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    OrganizationId,
    StaffEmail,
    StaffInvitationId,
    StaffRole,
    StaffUserId,
)
from apps.organization.infrastructure.models import StaffInvitationModel

__all__ = ["StaffInvitationMapper"]


class StaffInvitationMapper:
    """Bidirectional translator between ``StaffInvitation`` and its model."""

    @staticmethod
    def to_domain(model: StaffInvitationModel) -> StaffInvitation:
        """Reconstruct the aggregate from a persisted row (no re-validation, no events)."""
        return StaffInvitation.rehydrate(
            invitation_id=StaffInvitationId.from_uuid(model.id),
            organization_id=OrganizationId.from_uuid(model.organization_id),
            email=StaffEmail(model.email),
            role=StaffRole(model.role),
            token_hash=InvitationTokenHash(model.token_hash),
            expires_at=model.expires_at,
            invited_by=StaffUserId.from_uuid(model.invited_by),
            created_at=model.created_at,
            updated_at=model.updated_at,
            accepted_at=model.accepted_at,
            revoked_at=model.revoked_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: StaffInvitation) -> StaffInvitationModel:
        """Build a brand-new, unsaved ``StaffInvitationModel`` from an aggregate."""
        return StaffInvitationModel(**StaffInvitationMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: StaffInvitation) -> dict[str, object]:
        """Flatten an aggregate into ``StaffInvitationModel`` column values."""
        return {
            "id": entity.id.value,
            "organization_id": entity.organization_id.value,
            "email": entity.email.value,
            "role": entity.role.value,
            "token_hash": entity.token_hash.value,
            "expires_at": entity.expires_at,
            "invited_by": entity.invited_by.value,
            "accepted_at": entity.accepted_at,
            "revoked_at": entity.revoked_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }
