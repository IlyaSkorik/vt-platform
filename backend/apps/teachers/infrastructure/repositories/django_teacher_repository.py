"""``DjangoTeacherRepository`` - the ORM-backed adapter for the ``Teacher`` aggregate.

The single component permitted to touch the Django ORM on behalf of the ``Teacher``
aggregate. Use cases speak only ``Teacher`` and value objects; this adapter turns
those into ``TeacherModel`` queries and back via :class:`TeacherMapper`, opening a
transaction for a consistent read-then-write and translating every Django exception
into a :mod:`~apps.teachers.infrastructure.repositories.exceptions` type.

**Optimistic concurrency.** :meth:`save` writes conditionally on the *previous*
version, so a write built from a stale read updates zero rows and surfaces as
:class:`ConcurrencyConflictError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.db import DatabaseError, IntegrityError, transaction

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.value_objects import OwnerId, TeacherId, TeacherStatus
from apps.teachers.infrastructure.mappers import TeacherMapper
from apps.teachers.infrastructure.models import TeacherModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoTeacherRepository"]


class DjangoTeacherRepository:
    """Django ORM adapter implementing the ``TeacherRepository`` port.

    Stateless and cheap to construct. Structurally satisfies the port (it does not
    inherit the ``Protocol``, keeping the application core free of a dependency edge
    pointing at this module).
    """

    def get(self, teacher_id: TeacherId) -> Teacher | None:
        """Return the teacher with ``teacher_id`` (any non-deleted state), or ``None``."""
        try:
            model = TeacherModel.objects.filter(deleted_at__isnull=True).get(pk=teacher_id.value)
        except TeacherModel.DoesNotExist:
            return None
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load teacher {teacher_id}.") from exc
        return TeacherMapper.to_domain(model)

    def list_for_owner(self, owner_id: OwnerId, *, include_archived: bool = False) -> Sequence[Teacher]:
        """Return the owner's directory entries, newest first, optionally with archived ones."""
        try:
            query = TeacherModel.objects.filter(deleted_at__isnull=True, owner_id=owner_id.value)
            if not include_archived:
                query = query.filter(status=TeacherStatus.ACTIVE.value)
            models = list(query.order_by("-created_at", "id"))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list teachers for owner.") from exc
        return [TeacherMapper.to_domain(model) for model in models]

    def save(self, teacher: Teacher) -> None:
        """Persist ``teacher`` (insert or update), honouring its optimistic version."""
        model = TeacherMapper.to_model(teacher)
        values = self._column_values(model)
        update_values = {name: value for name, value in values.items() if name != "id"}
        previous_version = teacher.version - 1
        try:
            with transaction.atomic():
                updated = TeacherModel.objects.filter(pk=teacher.id.value, version=previous_version).update(**update_values)
                if not updated:
                    if TeacherModel.objects.filter(pk=teacher.id.value).exists():
                        raise ConcurrencyConflictError(f"Teacher {teacher.id} was modified concurrently; expected version {previous_version}.")
                    TeacherModel.objects.create(**values)
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist teacher {teacher.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist teacher {teacher.id}.") from exc

    @staticmethod
    def _column_values(model: TeacherModel) -> dict[str, object]:
        """Flatten a mapped ``TeacherModel`` into its concrete column values."""
        return {field.attname: getattr(model, field.attname) for field in TeacherModel._meta.concrete_fields}
