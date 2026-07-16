"""``TeacherMapper`` - the ACL between the ``Teacher`` aggregate and its ORM row.

The single component permitted to know both the framework-free domain and the
Django persistence model. Its whole job is translation:

* :meth:`to_domain`   - a row -> aggregate via :meth:`Teacher.rehydrate`.
* :meth:`to_model`    - aggregate -> a new, unsaved ``TeacherModel``.
* :meth:`update_model`- project an aggregate onto an existing ``TeacherModel``.

It never validates business rules, runs a workflow, publishes events, or calls
``save()``.
"""

from __future__ import annotations

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.value_objects import (
    EmailAddress,
    OwnerId,
    PersonName,
    PhoneNumber,
    TeacherId,
    TeacherRole,
    TeacherStatus,
)
from apps.teachers.infrastructure.models import TeacherModel

__all__ = ["TeacherMapper"]


class TeacherMapper:
    """Bidirectional, stateless translator between the ``Teacher`` aggregate and its row."""

    @staticmethod
    def to_domain(model: TeacherModel) -> Teacher:
        """Reconstruct the ``Teacher`` aggregate from its row (no re-validation, no events)."""
        return Teacher.rehydrate(
            teacher_id=TeacherId.from_uuid(model.id),
            owner_id=OwnerId.from_uuid(model.owner_id),
            name=PersonName(first_name=model.first_name, last_name=model.last_name, middle_name=model.middle_name),
            role=TeacherRole(model.role),
            status=TeacherStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=EmailAddress(model.email) if model.email is not None else None,
            phone=PhoneNumber(model.phone) if model.phone is not None else None,
            archived_at=model.archived_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Teacher) -> TeacherModel:
        """Build a brand-new, **unsaved** ``TeacherModel`` from an aggregate."""
        return TeacherModel(**TeacherMapper._to_columns(entity))

    @staticmethod
    def update_model(model: TeacherModel, entity: Teacher) -> TeacherModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it."""
        for field, value in TeacherMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def _to_columns(entity: Teacher) -> dict[str, object]:
        """Flatten an aggregate into the ``TeacherModel`` column values."""
        return {
            "id": entity.id.value,
            "owner_id": entity.owner_id.value,
            "first_name": entity.name.first_name,
            "last_name": entity.name.last_name,
            "middle_name": entity.name.middle_name,
            "role": entity.role.value,
            "email": entity.email.value if entity.email is not None else None,
            "phone": entity.phone.value if entity.phone is not None else None,
            "status": entity.status.value,
            "archived_at": entity.archived_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }
