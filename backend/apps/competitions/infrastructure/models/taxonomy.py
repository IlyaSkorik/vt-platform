"""Taxonomy child rows of the :class:`Competition` aggregate.

Persistence only (ARCH-001 §7.2, §14): ``Category``, ``Discipline``,
``AgeCategory`` and ``ParticipantGroup`` child entities as tables keyed to their
competition by a real foreign key. Sibling references within the aggregate
(a discipline's or group's ``category_id``) are plain UUID columns, not foreign
keys: the domain references siblings by id and the aggregate root guarantees their
referential integrity, so the repository can synchronize the child tables in any
order without cross-child FK constraints.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = [
    "AgeCategoryModel",
    "CategoryModel",
    "DisciplineModel",
    "ParticipantGroupModel",
]


class CategoryModel(BasePersistenceModel):
    """Database row for a competition category (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=120)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_category"
        verbose_name = "category"
        verbose_name_plural = "categories"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["competition", "name"], name="competitions_unique_category_name"),
        ]

    def __str__(self) -> str:
        return self.name


class DisciplineModel(BasePersistenceModel):
    """Database row for a discipline within a category (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="disciplines",
    )
    category_id = models.UUIDField()
    name = models.CharField(max_length=120)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_discipline"
        verbose_name = "discipline"
        verbose_name_plural = "disciplines"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["category_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["competition", "category_id", "name"], name="competitions_unique_discipline_name"),
        ]

    def __str__(self) -> str:
        return self.name


class AgeCategoryModel(BasePersistenceModel):
    """Database row for an age band (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="age_categories",
    )
    min_age = models.PositiveSmallIntegerField()
    max_age = models.PositiveSmallIntegerField()

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_age_category"
        verbose_name = "age category"
        verbose_name_plural = "age categories"

    def __str__(self) -> str:
        return f"{self.min_age}-{self.max_age}"


class ParticipantGroupModel(BasePersistenceModel):
    """Database row for a participant group (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="participant_groups",
    )
    category_id = models.UUIDField()
    name = models.CharField(max_length=120)
    min_count = models.PositiveIntegerField()
    max_count = models.PositiveIntegerField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_participant_group"
        verbose_name = "participant group"
        verbose_name_plural = "participant groups"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["category_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["competition", "category_id", "name"], name="competitions_unique_group_name"),
        ]

    def __str__(self) -> str:
        return self.name
