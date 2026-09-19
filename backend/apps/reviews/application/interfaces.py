"""Application ports (contracts) required by Reviews use cases.

Pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these; concrete adapters live under ``infrastructure/`` and
are injected at composition time. **Framework-free**: standard library only.

Two are windows onto other contexts, and both are read-only by design.
:class:`FestivalCatalog` is how the page offers a list of the organizer's
festivals to pick from — and how the chosen one's title is frozen onto the note.
:class:`OrganizationDirectory` supplies the name at the top of the public page, so
somebody who scanned a code on a banner can see whose page they landed on before
they start typing.

Storing a photograph is deliberately *not* a port here. Files arrive already
written, as references: the upload is an HTTP fact handled at the edge (where the
size, the media type and the throttle live), and a use case that could write to a
bucket would be a use case that has to be mocked to test a sentence of text.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.reviews.domain.entities import Review, ReviewPage

__all__ = [
    "CatalogFestival",
    "Clock",
    "FestivalCatalog",
    "OrganizationDirectory",
    "ReviewPageRepository",
    "ReviewRepository",
    "SlugFactory",
    "UuidGenerator",
]


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, always timezone-aware UTC."""

    def utcnow(self) -> datetime: ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: fresh time-ordered identifiers."""

    def new(self) -> uuid.UUID: ...


@runtime_checkable
class SlugFactory(Protocol):
    """Port: mint a candidate public slug (the caller checks it is free)."""

    def new_slug(self) -> str: ...


@runtime_checkable
class ReviewPageRepository(Protocol):
    """Port: persistence & retrieval of :class:`ReviewPage` aggregates."""

    def get_for_organization(self, organization_id: uuid.UUID) -> ReviewPage | None: ...

    def find_by_slug(self, slug: str) -> ReviewPage | None: ...

    def slug_exists(self, slug: str) -> bool: ...

    def save(self, page: ReviewPage) -> None: ...


@runtime_checkable
class ReviewRepository(Protocol):
    """Port: the append-only record of notes left on a page.

    ``list_everywhere`` serves the platform operator and nobody else — it is the
    one read in this context not scoped to an organization, which is why it is a
    method of its own rather than an optional argument that could default wrong.
    """

    def add(self, review: Review) -> None: ...

    def get(self, review_id: uuid.UUID) -> Review | None: ...

    def list_for_organization(self, organization_id: uuid.UUID, *, limit: int | None = None) -> Sequence[Review]: ...

    def list_everywhere(self, *, limit: int | None = None) -> Sequence[Review]: ...

    def count_for_organization(self, organization_id: uuid.UUID) -> int: ...

    def soft_delete(self, review: Review, *, now: datetime) -> None: ...


@dataclass(frozen=True, slots=True)
class CatalogFestival:
    """One festival a note may be filed under, in this context's own language."""

    id: uuid.UUID
    title: str


@runtime_checkable
class FestivalCatalog(Protocol):
    """Port: the organizer's own festivals, for the optional picker on the page."""

    def festivals_of(self, organization_id: uuid.UUID) -> Sequence[CatalogFestival]: ...

    def title_of(self, competition_id: uuid.UUID, *, organization_id: uuid.UUID) -> str | None: ...


@runtime_checkable
class OrganizationDirectory(Protocol):
    """Port: whose page this is, as the visitor should see it named."""

    def name_of(self, organization_id: uuid.UUID) -> str | None: ...
