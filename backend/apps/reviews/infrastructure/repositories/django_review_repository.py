"""``DjangoReviewRepository`` — ORM adapter for the append-only notes.

Notes are inserted and never updated, so there is no version guard here and no
``save``: :meth:`add` is the only write, and removal is a soft delete. That is not
an omission — a review the organizer could rewrite would not be a review.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from django.db import DatabaseError, IntegrityError

from apps.reviews.domain.entities import Review
from apps.reviews.infrastructure.mappers import ReviewMapper
from apps.reviews.infrastructure.models import ReviewModel

from .exceptions import IntegrityViolationError, PersistenceError

__all__ = ["DjangoReviewRepository"]


class DjangoReviewRepository:
    """Django ORM adapter implementing the ``ReviewRepository`` port."""

    def add(self, review: Review) -> None:
        """Insert one note."""
        try:
            ReviewModel.objects.create(**ReviewMapper.to_columns(review))
            review.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to store the review {review.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to store the review {review.id}.") from exc

    def get(self, review_id: uuid.UUID) -> Review | None:
        """One note, or ``None`` if it is gone."""
        try:
            model = ReviewModel.objects.filter(pk=review_id, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load the review {review_id}.") from exc
        return ReviewMapper.to_domain(model) if model is not None else None

    def list_for_organization(self, organization_id: uuid.UUID, *, limit: int | None = None) -> Sequence[Review]:
        """This organization's notes, newest first."""
        try:
            query = ReviewModel.objects.filter(organization_id=organization_id, deleted_at__isnull=True).order_by("-submitted_at")
            models = list(query[:limit] if limit else query)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list reviews.") from exc
        return [ReviewMapper.to_domain(model) for model in models]

    def list_everywhere(self, *, limit: int | None = None) -> Sequence[Review]:
        """Every note on the platform, newest first — the operator's read only."""
        try:
            query = ReviewModel.objects.filter(deleted_at__isnull=True).order_by("-submitted_at")
            models = list(query[:limit] if limit else query)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list reviews.") from exc
        return [ReviewMapper.to_domain(model) for model in models]

    def count_for_organization(self, organization_id: uuid.UUID) -> int:
        """How many notes this organization has — the number on the page card."""
        try:
            return ReviewModel.objects.filter(organization_id=organization_id, deleted_at__isnull=True).count()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to count reviews.") from exc

    def soft_delete(self, review: Review, *, now: datetime) -> None:
        """Remove a note from every list without erasing the row.

        The row stays because the consent recorded on it is the answer to "on what
        basis was this held, and when did it stop being shown" — a question a hard
        delete makes unanswerable.
        """
        try:
            ReviewModel.objects.filter(pk=review.id).update(deleted_at=now, updated_at=now)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete the review {review.id}.") from exc
