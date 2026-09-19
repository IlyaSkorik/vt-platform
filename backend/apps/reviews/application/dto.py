"""Read views returned by the Reviews use cases.

Flat, framework-free projections (ARCH-001 §7.3) — the REST edge renders these
and never touches an aggregate. Photographs travel as stored references; turning
one into an address a browser can open is the edge's job, because only the edge
knows what the storage is today.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

__all__ = ["FestivalOption", "PublicPageView", "ReviewPageView", "ReviewView"]


@dataclass(frozen=True, slots=True)
class FestivalOption:
    """One entry in the optional "о каком фестивале" picker."""

    id: str
    title: str


@dataclass(frozen=True, slots=True)
class ReviewPageView:
    """The page as its owner administers it."""

    id: str
    organization_id: str
    slug: str
    title: str
    intro: str
    accepting: bool
    created_at: datetime
    updated_at: datetime
    #: How many notes have been left. The one number the organizer looks for.
    review_count: int = 0


@dataclass(frozen=True, slots=True)
class PublicPageView:
    """The page as a stranger with a phone sees it.

    Carries no id and no organization id: the slug is the only handle the public
    side has, and shipping internal identifiers to a page that anyone can open is
    how they end up being guessed at somewhere else.

    ``accepting`` false still renders — the banner is printed, and a link that
    explains itself beats one that 404s.
    """

    slug: str
    title: str
    intro: str
    organization_name: str
    accepting: bool
    festivals: Sequence[FestivalOption] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ReviewView:
    """One note as the organizer (or the platform operator) reads it."""

    id: str
    organization_id: str
    author_name: str | None
    text: str
    photos: Sequence[str]
    competition_id: str | None
    competition_title: str | None
    submitted_at: datetime
    consent_code: str
    consent_version: str
    consent_accepted_at: datetime
    #: Filled only for the operator's console, which spans organizations and has to
    #: say whose note each one is. Empty in the organizer's own list, where the
    #: answer is always "yours".
    organization_name: str | None = None
