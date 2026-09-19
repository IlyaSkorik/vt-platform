"""``DjangoReviewPageRepository`` — ORM adapter for the ``ReviewPage`` aggregate.

One row per organization, rewritten in place. The write is guarded on the version
the aggregate was read at, so two staff members editing the page from two tabs
cannot silently overwrite one another.
"""

from __future__ import annotations

import uuid

from django.db import DatabaseError, IntegrityError, transaction

from apps.reviews.domain.entities import ReviewPage
from apps.reviews.infrastructure.mappers import ReviewPageMapper
from apps.reviews.infrastructure.models import ReviewPageModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoReviewPageRepository"]


class DjangoReviewPageRepository:
    """Django ORM adapter implementing the ``ReviewPageRepository`` port."""

    def get_for_organization(self, organization_id: uuid.UUID) -> ReviewPage | None:
        """The organization's page, or ``None`` if it has never opened one."""
        try:
            model = ReviewPageModel.objects.filter(organization_id=organization_id, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load the review page of {organization_id}.") from exc
        return ReviewPageMapper.to_domain(model) if model is not None else None

    def find_by_slug(self, slug: str) -> ReviewPage | None:
        """The page behind a public link, or ``None``.

        The public read path. A soft-deleted page is not found, which is what makes
        retiring a link work.
        """
        try:
            model = ReviewPageModel.objects.filter(slug=slug, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to load the review page by slug.") from exc
        return ReviewPageMapper.to_domain(model) if model is not None else None

    def slug_exists(self, slug: str) -> bool:
        """Whether the slug is claimed — including by a deleted page.

        Deleted rows count: a link printed on a banner and later retired must never
        be minted again for somebody else's page.
        """
        try:
            return ReviewPageModel.objects.filter(slug=slug).exists()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to check slug.") from exc

    def save(self, page: ReviewPage) -> None:
        """Insert or update the page's row, guarded on its read version."""
        columns = ReviewPageMapper.to_columns(page)
        expected = page.persisted_version
        try:
            with transaction.atomic():
                if expected is None:
                    ReviewPageModel.objects.create(**columns)
                else:
                    updated = ReviewPageModel.objects.filter(pk=page.id, version=expected).update(
                        **{name: value for name, value in columns.items() if name != "id"}
                    )
                    if not updated:
                        raise ConcurrencyConflictError(f"Review page {page.id} was modified concurrently; expected version {expected}.")
                page.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist the review page {page.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist the review page {page.id}.") from exc
