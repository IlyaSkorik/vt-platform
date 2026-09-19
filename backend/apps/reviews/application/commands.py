"""Command objects for the Reviews use cases.

Plain frozen dataclasses of primitives (ARCH-001 §7.3): the edge parses HTTP into
one of these, the service turns it into domain values. Nothing here validates —
a command that policed its own fields would be a second, quieter copy of the
value objects, and the two would drift.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

__all__ = ["SubmitReviewCommand", "UpdateReviewPageCommand"]


@dataclass(frozen=True, slots=True)
class SubmitReviewCommand:
    """A note arriving from the public page.

    ``slug`` is the only thing identifying where it belongs, because it is the only
    thing the sender has. ``consent_code`` and ``consent_version`` are what the form
    declared the person accepted; the service pairs them with the instant they
    arrived, and refuses the whole note if either is missing.

    ``photos`` are storage references, already written by the edge.
    """

    slug: str
    text: str
    consent_code: str
    consent_version: str
    author_name: str | None = None
    competition_id: str | None = None
    photos: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class UpdateReviewPageCommand:
    """The organizer rewording their page, or opening and closing collection.

    Every field is optional and ``None`` means "leave as it was": the settings form
    and the open/close switch are two controls on one screen, and neither should
    have to resend the other's value to avoid clobbering it.
    """

    organization_id: str
    title: str | None = None
    intro: str | None = None
    accepting: bool | None = None
