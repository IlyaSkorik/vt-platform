"""Domain exceptions for the Reviews bounded context.

Every error carries a stable ``code``, which is what the REST edge maps onto an
RFC 9457 problem type (API-000 §8). Messages are the ones a person reads, so they
are written in Russian and say what to do rather than what went wrong internally.
"""

from __future__ import annotations

from typing import ClassVar

__all__ = [
    "ConsentRequiredError",
    "InvalidReviewDataError",
    "ReviewError",
    "ReviewNotFoundError",
    "ReviewPageClosedError",
    "ReviewPageNotFoundError",
    "SlugUnavailableError",
]


class ReviewError(Exception):
    """Base class for every failure this context reports."""

    code: ClassVar[str] = "review_error"


class ReviewPageNotFoundError(ReviewError):
    """No page answers that link.

    The same answer covers a page that never existed, one whose link was revoked
    and one that belongs to somebody else — a link that behaved differently for
    each would be a way to probe for pages by trying.
    """

    code: ClassVar[str] = "review_page_not_found"


class ReviewNotFoundError(ReviewError):
    """No such review, or none the caller is allowed to know about."""

    code: ClassVar[str] = "review_not_found"


class InvalidReviewDataError(ReviewError, ValueError):
    """A value the domain refuses: an empty note, an overlong name, a sixth photo."""

    code: ClassVar[str] = "invalid_review_data"


class ReviewPageClosedError(ReviewError):
    """The organizer has stopped collecting; the page reads but does not accept.

    Separate from "not found" on purpose: the banner is already printed and the
    link stays valid, so somebody scanning it deserves to be told that the season
    is over rather than shown a dead end.
    """

    code: ClassVar[str] = "review_page_closed"


class ConsentRequiredError(ReviewError):
    """A note arrived without the consent its own storage depends on.

    Refused in the domain rather than in a serializer: the consent version is part
    of the record (LEGAL-001 §13.3), and a :class:`Review` that could exist without
    one would be a row the platform cannot justify holding.
    """

    code: ClassVar[str] = "consent_required"


class SlugUnavailableError(ReviewError):
    """Could not mint a free public link (astronomically unlikely; not silent)."""

    code: ClassVar[str] = "slug_unavailable"
