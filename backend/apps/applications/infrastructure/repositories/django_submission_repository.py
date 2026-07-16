"""``DjangoSubmissionRepository`` - the ORM-backed adapter for the ``Submission`` aggregate.

The single component permitted to touch the Django ORM on behalf of ``Submission``.
Translates aggregates to/from ``SubmissionModel`` via :class:`SubmissionMapper`,
opens a transaction for a consistent read-then-write, honours the root's optimistic
``version`` (a stale write updates zero rows -> :class:`ConcurrencyConflictError`),
and translates every Django exception into a repository-layer type.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.db import DatabaseError, IntegrityError, transaction

from apps.applications.domain.entities import Submission
from apps.applications.domain.value_objects import CompetitionId, SubmissionId, UserId
from apps.applications.infrastructure.mappers import SubmissionMapper
from apps.applications.infrastructure.models import SubmissionModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoSubmissionRepository"]


class DjangoSubmissionRepository:
    """Django ORM adapter implementing the ``SubmissionRepository`` port."""

    def get(self, submission_id: SubmissionId) -> Submission | None:
        try:
            model = SubmissionModel.objects.filter(deleted_at__isnull=True).get(pk=submission_id.value)
        except SubmissionModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load submission {submission_id}.") from exc
        return SubmissionMapper.to_domain(model)

    def exists(self, submission_id: SubmissionId) -> bool:
        try:
            return SubmissionModel.objects.filter(pk=submission_id.value, deleted_at__isnull=True).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to check existence of {submission_id}.") from exc

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Submission]:
        try:
            models = list(SubmissionModel.objects.filter(deleted_at__isnull=True, applicant_id=applicant_id.value).order_by("-created_at", "id"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list submissions for applicant.") from exc
        return [SubmissionMapper.to_domain(model) for model in models]

    def list_by_competition(self, competition_id: CompetitionId) -> Sequence[Submission]:
        try:
            models = list(SubmissionModel.objects.filter(deleted_at__isnull=True, competition_id=competition_id.value).order_by("-created_at", "id"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list submissions for competition.") from exc
        return [SubmissionMapper.to_domain(model) for model in models]

    def save(self, submission: Submission) -> None:
        model = SubmissionMapper.to_model(submission)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        # Match on the version the aggregate was loaded at, not ``version - 1``: a
        # single use case (e.g. update-teacher = add + remove) may bump the version
        # more than once before one save, so the pre-image is the loaded version and
        # the new value is the current version.
        expected_version = submission.initial_version
        try:
            with transaction.atomic():
                updated = SubmissionModel.objects.filter(pk=submission.id.value, version=expected_version).update(**update_values)
                if not updated:
                    if SubmissionModel.objects.filter(pk=submission.id.value).exists():
                        raise ConcurrencyConflictError(f"Submission {submission.id} was modified concurrently; expected version {expected_version}.")
                    SubmissionModel.objects.create(**values)
            submission.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist submission {submission.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist submission {submission.id}.") from exc

    def delete(self, submission_id: SubmissionId) -> None:
        """Hard-delete a draft submission (reserved for never-submitted drafts)."""
        try:
            with transaction.atomic():
                SubmissionModel.objects.filter(pk=submission_id.value).delete()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete submission {submission_id}.") from exc

    @staticmethod
    def _column_values(model: SubmissionModel) -> dict[str, object]:
        return {field.attname: getattr(model, field.attname) for field in SubmissionModel._meta.concrete_fields}
