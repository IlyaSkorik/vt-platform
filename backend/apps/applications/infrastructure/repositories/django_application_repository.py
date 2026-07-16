"""``DjangoApplicationRepository`` - the ORM-backed adapter for the ``Application`` aggregate.

Translates the order aggregate to/from ``ApplicationModel`` via
:class:`ApplicationMapper`, honouring the root's optimistic ``version`` and
translating Django exceptions into repository-layer types. It never loads the
referenced Submissions - those are a separate aggregate.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.db import DatabaseError, IntegrityError, transaction

from apps.applications.domain.entities import Application
from apps.applications.domain.value_objects import ApplicationId, UserId
from apps.applications.infrastructure.mappers import ApplicationMapper
from apps.applications.infrastructure.models import ApplicationModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoApplicationRepository"]


class DjangoApplicationRepository:
    """Django ORM adapter implementing the ``ApplicationRepository`` port."""

    def get(self, application_id: ApplicationId) -> Application | None:
        try:
            model = ApplicationModel.objects.filter(deleted_at__isnull=True).get(pk=application_id.value)
        except ApplicationModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load application {application_id}.") from exc
        return ApplicationMapper.to_domain(model)

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Application]:
        try:
            models = list(ApplicationModel.objects.filter(deleted_at__isnull=True, applicant_id=applicant_id.value).order_by("-created_at", "id"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list applications for applicant.") from exc
        return [ApplicationMapper.to_domain(model) for model in models]

    def save(self, application: Application) -> None:
        model = ApplicationMapper.to_model(application)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        # Match on the version the aggregate was loaded at, not ``version - 1``: a
        # single use case may bump the version several times before one save, so the
        # pre-image is the loaded version and the new value is the current version.
        expected_version = application.initial_version
        try:
            with transaction.atomic():
                updated = ApplicationModel.objects.filter(pk=application.id.value, version=expected_version).update(**update_values)
                if not updated:
                    if ApplicationModel.objects.filter(pk=application.id.value).exists():
                        raise ConcurrencyConflictError(
                            f"Application {application.id} was modified concurrently; expected version {expected_version}."
                        )
                    ApplicationModel.objects.create(**values)
            application.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist application {application.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist application {application.id}.") from exc

    @staticmethod
    def _column_values(model: ApplicationModel) -> dict[str, object]:
        return {field.attname: getattr(model, field.attname) for field in ApplicationModel._meta.concrete_fields}
