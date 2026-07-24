"""Django adapter implementing the ``DiplomaRepository`` port.

Numbers are sequential, zero-padded and permanent. They are derived as
``max(number) + 1`` (fixed-width zero-padding makes the lexicographic max the
numeric max), which is portable across PostgreSQL and the test SQLite. The
unconditional unique constraint on ``number`` is the correctness backstop: a
concurrent collision surfaces as an ``IntegrityError`` rather than a duplicate.
"""

from __future__ import annotations

import uuid

from apps.diplomas.domain.entities import Diploma
from apps.diplomas.infrastructure.mappers import DiplomaMapper
from apps.diplomas.infrastructure.models import DiplomaModel
from apps.diplomas.infrastructure.models.base import uuid7

__all__ = ["DjangoDiplomaRepository"]

#: Zero-pad width for diploma numbers (six digits: 000001, 000002, …).
_NUMBER_WIDTH = 6


class DjangoDiplomaRepository:
    """Concrete ``DiplomaRepository`` over the Django ORM."""

    def new_id(self) -> uuid.UUID:
        return uuid7()

    def next_number(self) -> str:
        last = DiplomaModel.objects.order_by("-number").values_list("number", flat=True).first()
        current = int(last) if last and last.isdigit() else 0
        return f"{current + 1:0{_NUMBER_WIDTH}d}"

    def exists_for_submission(self, submission_id: uuid.UUID) -> bool:
        return DiplomaModel.objects.filter(
            submission_id=submission_id, deleted_at__isnull=True
        ).exists()

    def add(self, diploma: Diploma) -> None:
        DiplomaMapper.to_model(diploma).save(force_insert=True)

    def update(self, diploma: Diploma) -> None:
        model = DiplomaModel.objects.filter(id=diploma.id).first()
        if model is None:
            return
        DiplomaMapper.update_model(model, diploma).save()

    def get(self, diploma_id: uuid.UUID) -> Diploma | None:
        model = DiplomaModel.objects.filter(id=diploma_id, deleted_at__isnull=True).first()
        return DiplomaMapper.to_domain(model) if model is not None else None

    def get_by_submission(self, submission_id: uuid.UUID) -> Diploma | None:
        model = DiplomaModel.objects.filter(
            submission_id=submission_id, deleted_at__isnull=True
        ).first()
        return DiplomaMapper.to_domain(model) if model is not None else None

    def list_by_competition(self, competition_id: uuid.UUID) -> list[Diploma]:
        rows = DiplomaModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("-created_at")
        return [DiplomaMapper.to_domain(row) for row in rows]
