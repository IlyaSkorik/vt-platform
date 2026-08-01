"""``DjangoOrganizationRepository`` — ORM adapter for the ``Organization`` aggregate."""

from __future__ import annotations

from django.db import DatabaseError

from apps.organization.domain.entities import Organization
from apps.organization.domain.value_objects import OrganizationId
from apps.organization.infrastructure.mappers import OrganizationMapper
from apps.organization.infrastructure.models import OrganizationModel

from ._upsert import optimistic_upsert
from .exceptions import PersistenceError

__all__ = ["DjangoOrganizationRepository"]


class DjangoOrganizationRepository:
    """Django ORM adapter implementing the ``OrganizationRepository`` port.

    Stateless. Structurally satisfies the port (no ``Protocol`` inheritance — the
    seam is structural by design).
    """

    def get(self, organization_id: OrganizationId) -> Organization | None:
        """Return the organization with ``organization_id``, or ``None``."""
        try:
            model = OrganizationModel.objects.get(pk=organization_id.value)
        except OrganizationModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load organization {organization_id}.") from exc
        return OrganizationMapper.to_domain(model)

    def get_default(self) -> Organization | None:
        """Return the platform's own organization, or ``None`` if not yet seeded.

        The earliest-created active row: the one the seed migration wrote, before
        the platform operator connected any others. Only the bootstrap path uses
        it — everything staff-facing resolves the caller's own organization.
        """
        try:
            model = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load the default organization.") from exc
        return OrganizationMapper.to_domain(model) if model is not None else None

    def find_by_slug(self, slug: str) -> Organization | None:
        """Return the organization holding ``slug``, or ``None``.

        The uniqueness check for connecting a new organization: the slug is the
        URL identity, so a collision has to be refused before anything is written.
        """
        try:
            model = OrganizationModel.objects.filter(slug=slug, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load the organization with slug {slug!r}.") from exc
        return OrganizationMapper.to_domain(model) if model is not None else None

    def list_all(self) -> list[Organization]:
        """Return every connected organization, oldest first."""
        try:
            models = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at")
            return [OrganizationMapper.to_domain(model) for model in models]
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list organizations.") from exc

    def save(self, organization: Organization) -> None:
        """Persist ``organization`` (insert or update), honouring its version."""
        model = OrganizationMapper.to_model(organization)
        optimistic_upsert(
            model_cls=OrganizationModel,
            pk=organization.id.value,
            version=organization.version,
            columns=_column_values(model),
        )


def _column_values(model: OrganizationModel) -> dict[str, object]:
    """Flatten a mapped model into its concrete column values."""
    return {field.attname: getattr(model, field.attname) for field in OrganizationModel._meta.concrete_fields}
