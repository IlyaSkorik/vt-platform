"""ORM adapter for the :class:`PlatformAdministrator` aggregate."""

from __future__ import annotations

from apps.platform.domain.entities import PlatformAdministrator
from apps.platform.domain.value_objects import PlatformAdministratorId, PlatformUserId
from apps.platform.infrastructure.models import PlatformAdministratorModel

__all__ = ["DjangoPlatformAdministratorRepository"]


def _to_domain(model: PlatformAdministratorModel) -> PlatformAdministrator:
    return PlatformAdministrator.rehydrate(
        administrator_id=PlatformAdministratorId.from_uuid(model.id),
        user_id=PlatformUserId.from_uuid(model.user_id),
        granted_at=model.granted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        revoked_at=model.revoked_at,
        deleted_at=model.deleted_at,
        version=model.version,
    )


class DjangoPlatformAdministratorRepository:
    """Django ORM adapter implementing the ``PlatformAdministratorRepository`` port.

    Stateless, and structurally satisfying the port (no ``Protocol`` inheritance —
    the seam is structural by design).
    """

    def find_by_user(self, user_id: PlatformUserId) -> PlatformAdministrator | None:
        model = PlatformAdministratorModel.objects.filter(user_id=user_id.value, deleted_at__isnull=True).first()
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[PlatformAdministrator]:
        rows = PlatformAdministratorModel.objects.filter(deleted_at__isnull=True).order_by("created_at")
        return [_to_domain(row) for row in rows]

    def save(self, administrator: PlatformAdministrator) -> None:
        PlatformAdministratorModel.objects.update_or_create(
            pk=administrator.id.value,
            defaults={
                "user_id": administrator.user_id.value,
                "granted_at": administrator.granted_at,
                "revoked_at": administrator.revoked_at,
                "created_at": administrator.created_at,
                "updated_at": administrator.updated_at,
                "deleted_at": administrator.deleted_at,
                "version": administrator.version,
            },
        )
