"""Mappers — the ACL between the Reviews aggregates and their rows.

The only components permitted to know both the framework-free aggregates and
their Django models. They translate in both directions and do nothing else: no
validation, no workflow, no ``save()``. Timestamps are copied verbatim — the
aggregates own those instants.
"""

from __future__ import annotations

from typing import Any

from apps.reviews.domain.entities import Review, ReviewPage
from apps.reviews.domain.value_objects import (
    AuthorName,
    ConsentRecord,
    PageIntro,
    PageTitle,
    PhotoReference,
    PublicSlug,
    ReviewText,
)
from apps.reviews.infrastructure.models import ReviewModel, ReviewPageModel

__all__ = ["ReviewMapper", "ReviewPageMapper"]


class ReviewPageMapper:
    """Bidirectional translator between ``ReviewPage`` and its row."""

    @staticmethod
    def to_domain(model: ReviewPageModel) -> ReviewPage:
        """Reconstruct the aggregate from its row (no re-validation, no events)."""
        return ReviewPage.rehydrate(
            page_id=model.id,
            organization_id=model.organization_id,
            slug=PublicSlug(model.slug),
            title=PageTitle(model.title),
            created_at=model.created_at,
            updated_at=model.updated_at,
            intro=PageIntro(model.intro),
            accepting=model.accepting,
            version=model.version,
        )

    @staticmethod
    def to_columns(page: ReviewPage) -> dict[str, Any]:
        """The aggregate as the columns of its row."""
        return {
            "id": page.id,
            "organization_id": page.organization_id,
            "slug": page.slug.value,
            "title": page.title.value,
            "intro": page.intro.value,
            "accepting": page.accepting,
            "created_at": page.created_at,
            "updated_at": page.updated_at,
            "version": page.version,
        }


class ReviewMapper:
    """Bidirectional translator between ``Review`` and its row."""

    @staticmethod
    def to_domain(model: ReviewModel) -> Review:
        """Reconstruct one note from its row.

        A stored photo reference that no longer parses is dropped rather than
        allowed to fail the whole read: one bad key in a list must not make a
        person's words unreadable.
        """
        photos = []
        for reference in model.photos or []:
            try:
                photos.append(PhotoReference(str(reference)))
            except ValueError:
                continue
        return Review.rehydrate(
            review_id=model.id,
            page_id=model.page_id,
            organization_id=model.organization_id,
            text=ReviewText(model.text),
            consent=ConsentRecord(code=model.consent_code, version=model.consent_version, accepted_at=model.consent_accepted_at),
            submitted_at=model.submitted_at,
            author=AuthorName.parse(model.author_name),
            competition_id=model.competition_id,
            competition_title=model.competition_title,
            photos=photos,
            version=model.version,
        )

    @staticmethod
    def to_columns(review: Review) -> dict[str, Any]:
        """The note as the columns of its row."""
        return {
            "id": review.id,
            "page_id": review.page_id,
            "organization_id": review.organization_id,
            "author_name": review.author.value if review.author is not None else None,
            "text": review.text.value,
            "photos": [photo.value for photo in review.photos],
            "competition_id": review.competition_id,
            "competition_title": review.competition_title,
            "consent_code": review.consent.code,
            "consent_version": review.consent.version,
            "consent_accepted_at": review.consent.accepted_at,
            "submitted_at": review.submitted_at,
            "created_at": review.submitted_at,
            "updated_at": review.submitted_at,
            "version": review.version,
        }
