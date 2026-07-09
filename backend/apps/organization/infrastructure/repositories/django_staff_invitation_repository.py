"""``DjangoStaffInvitationRepository`` — ORM adapter for the ``StaffInvitation`` aggregate."""

from __future__ import annotations

from django.db import DatabaseError

from apps.organization.domain.entities import StaffInvitation
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    OrganizationId,
    StaffEmail,
    StaffInvitationId,
)
from apps.organization.infrastructure.mappers import StaffInvitationMapper
from apps.organization.infrastructure.models import StaffInvitationModel

from ._upsert import optimistic_upsert
from .exceptions import PersistenceError

__all__ = ["DjangoStaffInvitationRepository"]


class DjangoStaffInvitationRepository:
    """Django ORM adapter implementing the ``StaffInvitationRepository`` port."""

    def get(self, invitation_id: StaffInvitationId) -> StaffInvitation | None:
        """Return the invitation with ``invitation_id``, or ``None``."""
        try:
            model = StaffInvitationModel.objects.get(pk=invitation_id.value)
        except StaffInvitationModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load invitation {invitation_id}.") from exc
        return StaffInvitationMapper.to_domain(model)

    def get_by_token_hash(self, token_hash: InvitationTokenHash) -> StaffInvitation | None:
        """Return the invitation whose token digest is ``token_hash``, or ``None``.

        The digest column is uniquely constrained, so at most one row matches.
        """
        try:
            model = StaffInvitationModel.objects.get(token_hash=token_hash.value)
        except StaffInvitationModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load invitation by token hash.") from exc
        return StaffInvitationMapper.to_domain(model)

    def find_pending_by_email(self, *, email: StaffEmail, organization_id: OrganizationId) -> StaffInvitation | None:
        """Return an open invitation for ``email`` in the organization, or ``None``.

        Open = neither accepted nor revoked nor soft-deleted; the partial unique
        constraint guarantees at most one such row.
        """
        try:
            model = StaffInvitationModel.objects.get(
                email=email.value,
                organization_id=organization_id.value,
                accepted_at__isnull=True,
                revoked_at__isnull=True,
                deleted_at__isnull=True,
            )
        except StaffInvitationModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load pending invitation by email.") from exc
        return StaffInvitationMapper.to_domain(model)

    def save(self, invitation: StaffInvitation) -> None:
        """Persist ``invitation`` (insert or update), honouring its version."""
        model = StaffInvitationMapper.to_model(invitation)
        optimistic_upsert(
            model_cls=StaffInvitationModel,
            pk=invitation.id.value,
            version=invitation.version,
            columns=_column_values(model),
        )


def _column_values(model: StaffInvitationModel) -> dict[str, object]:
    """Flatten a mapped model into its concrete column values."""
    return {field.attname: getattr(model, field.attname) for field in StaffInvitationModel._meta.concrete_fields}
