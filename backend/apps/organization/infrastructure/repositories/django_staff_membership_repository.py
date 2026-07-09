"""``DjangoStaffMembershipRepository`` — ORM adapter for the ``StaffMembership`` aggregate."""

from __future__ import annotations

from collections.abc import Sequence

from django.db import DatabaseError

from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import (
    MembershipStatus,
    OrganizationId,
    StaffMembershipId,
    StaffUserId,
)
from apps.organization.infrastructure.mappers import StaffMembershipMapper
from apps.organization.infrastructure.models import StaffMembershipModel

from ._upsert import optimistic_upsert
from .exceptions import PersistenceError

__all__ = ["DjangoStaffMembershipRepository"]


class DjangoStaffMembershipRepository:
    """Django ORM adapter implementing the ``StaffMembershipRepository`` port."""

    def get(self, membership_id: StaffMembershipId) -> StaffMembership | None:
        """Return the membership with ``membership_id``, or ``None``."""
        try:
            model = StaffMembershipModel.objects.get(pk=membership_id.value)
        except StaffMembershipModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load membership {membership_id}.") from exc
        return StaffMembershipMapper.to_domain(model)

    def find_active(self, *, user_id: StaffUserId, organization_id: OrganizationId) -> StaffMembership | None:
        """Return the user's ACTIVE membership in the organization, or ``None``.

        The authorization query. At most one row matches (the partial unique
        constraint guarantees one active membership per user per organization).
        """
        try:
            model = StaffMembershipModel.objects.get(
                user_id=user_id.value,
                organization_id=organization_id.value,
                status=MembershipStatus.ACTIVE.value,
                deleted_at__isnull=True,
            )
        except StaffMembershipModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load active membership.") from exc
        return StaffMembershipMapper.to_domain(model)

    def exists_active(self, *, user_id: StaffUserId, organization_id: OrganizationId) -> bool:
        """Whether the user already has an ACTIVE membership (uniqueness pre-check)."""
        try:
            return StaffMembershipModel.objects.filter(
                user_id=user_id.value,
                organization_id=organization_id.value,
                status=MembershipStatus.ACTIVE.value,
                deleted_at__isnull=True,
            ).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to check active membership.") from exc

    def list_by_organization(self, organization_id: OrganizationId) -> Sequence[StaffMembership]:
        """Return all non-deleted memberships of the organization (newest first)."""
        try:
            models = list(StaffMembershipModel.objects.filter(organization_id=organization_id.value, deleted_at__isnull=True).order_by("-created_at"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list memberships.") from exc
        return [StaffMembershipMapper.to_domain(model) for model in models]

    def save(self, membership: StaffMembership) -> None:
        """Persist ``membership`` (insert or update), honouring its version."""
        model = StaffMembershipMapper.to_model(membership)
        optimistic_upsert(
            model_cls=StaffMembershipModel,
            pk=membership.id.value,
            version=membership.version,
            columns=_column_values(model),
        )


def _column_values(model: StaffMembershipModel) -> dict[str, object]:
    """Flatten a mapped model into its concrete column values."""
    return {field.attname: getattr(model, field.attname) for field in StaffMembershipModel._meta.concrete_fields}
