"""``TeacherModel`` - persistence representation of the ``Teacher`` aggregate root.

Maps every field of ``apps.teachers.domain.entities.Teacher`` to a column. This is a
**persistence model only**: no invariants, transitions, or validation - the domain
aggregate owns all of that. Rows are scoped to their ``owner_id`` (the user who owns
the directory) and indexed for the per-owner listing the API serves.
"""

from __future__ import annotations

from django.db import models

from apps.teachers.domain.value_objects import TeacherStatus

from .base import BasePersistenceModel

__all__ = ["TeacherModel"]

_STATUS_CHOICES = [(status.value, status.name.title()) for status in TeacherStatus]


class TeacherModel(BasePersistenceModel):
    """Database row for a directory teacher (persistence only - no business logic)."""

    owner_id = models.UUIDField()

    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    middle_name = models.CharField(max_length=120, null=True, blank=True, default=None)

    role = models.CharField(max_length=120)
    email = models.CharField(max_length=320, null=True, blank=True, default=None)
    phone = models.CharField(max_length=32, null=True, blank=True, default=None)

    status = models.CharField(max_length=16, choices=_STATUS_CHOICES)
    archived_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "teachers_teacher"
        verbose_name = "teacher"
        verbose_name_plural = "teachers"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["owner_id", "status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in TeacherStatus]),
                name="teachers_teacher_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name} ({self.id})"
