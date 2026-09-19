"""Composition root for the Reviews bounded context.

The one place a framework-free use case is wired to its concrete adapters
(ARCH-001 §7.3, Dependency Inversion): the presentation edge asks here for an
assembled service and stays ignorant of which repository, clock or catalog sits
behind each port. Adapters are stateless and cheap, so they are assembled per call.
"""

from __future__ import annotations

from apps.reviews.application.services import ReviewService
from apps.reviews.infrastructure.acl import DjangoFestivalCatalog, DjangoOrganizationDirectory
from apps.reviews.infrastructure.repositories import DjangoReviewPageRepository, DjangoReviewRepository
from apps.reviews.infrastructure.system import RandomSlugFactory, SystemClock, Uuid7Generator

__all__ = ["build_review_service"]


def build_review_service() -> ReviewService:
    """Assemble the Reviews use cases over PostgreSQL and the real clock."""
    return ReviewService(
        pages=DjangoReviewPageRepository(),
        reviews=DjangoReviewRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        slugs=RandomSlugFactory(),
        festivals=DjangoFestivalCatalog(),
        organizations=DjangoOrganizationDirectory(),
    )
