"""Application ports (contracts) required by Applications (Competition Submission) use cases.

The **outbound dependencies** of the Applications application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these abstractions; concrete adapters (a Django ORM
repository, a Competition read-model gateway, a clock, a UUID source, an event
publisher) live in ``infrastructure/`` and are injected at composition time. The
dependency arrow points *inward*: infrastructure depends on this module, never the
reverse.

**Framework-free** (ARCH-001 §4.1, §7.2): standard library and this context's
domain only. Interfaces only, no implementations.

The :class:`Submission` is the sole aggregate root of this context, so there is a
single repository. It persists and retrieves the **whole aggregate** - the root
plus its child entities (participants, teachers, attachments, reviews) and its
value objects (the performance and the price snapshot) - as one unit, because they
share one consistency boundary.

**Anti-corruption gateways (ACL).** The Submission context never imports the
Competition, Organization or Identity aggregates. It reaches them only through the
read-model ports declared here:

* :class:`CompetitionCatalog` - the Competition context: whether a competition
  exists, whether it currently accepts submissions (status + deadlines), the
  participation policy (admissibility + participant-group limits) of a combination,
  and the per-participant price. Its :meth:`~CompetitionCatalog.participation_policy`
  returns a :class:`SubmissionParticipationPolicy` read model (a local projection),
  so the domain validates admissibility and count rules without importing the
  Competition aggregate.
* :class:`OrganizationReadModel` - the Organization context: whether a user holds
  staff permission and whether a reviewer is authorized to act as an organizer.
* :class:`IdentityReadModel` - the Identity context: whether the applicant user
  exists, and their display information.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.applications.domain.entities import Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    CompetitionId,
    DisciplineId,
    Money,
    NominationId,
    ParticipantGroupId,
    ParticipationFormatId,
    ReviewerId,
    SubmissionId,
    SubmissionParticipationPolicy,
    UserId,
)

__all__ = [
    "ApplicantInfo",
    "Clock",
    "CompetitionCatalog",
    "EventPublisher",
    "IdentityReadModel",
    "OrganizationReadModel",
    "SubmissionRepository",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Repository port
# ---------------------------------------------------------------------------


@runtime_checkable
class SubmissionRepository(Protocol):
    """Port: persistence & retrieval of the :class:`Submission` aggregate.

    Loads and saves the entire aggregate graph atomically, honouring the root's
    optimistic-concurrency ``version``. Getters report absence as ``None`` rather
    than raising, leaving the "not found" decision to the use case.
    """

    def get(self, submission_id: SubmissionId) -> Submission | None:
        """Return the submission with ``submission_id`` (whole aggregate), or ``None``."""
        ...

    def exists(self, submission_id: SubmissionId) -> bool:
        """Whether a submission with ``submission_id`` exists (no aggregate materialized)."""
        ...

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Submission]:
        """Return all non-deleted submissions owned by ``applicant_id``."""
        ...

    def list_by_competition(self, competition_id: CompetitionId) -> Sequence[Submission]:
        """Return all non-deleted submissions for ``competition_id``."""
        ...

    def save(self, submission: Submission) -> None:
        """Persist ``submission`` and its whole graph (insert or update), honouring its version."""
        ...

    def delete(self, submission_id: SubmissionId) -> None:
        """Delete the submission with ``submission_id``.

        Reserved for **draft** deletion: a never-submitted draft carries no business
        history to preserve. The domain deliberately exposes no delete transition,
        so the "only a draft may be deleted" precondition is enforced by the use
        case (via the aggregate's own ``is_draft`` predicate) before this is called.
        """
        ...


# ---------------------------------------------------------------------------
# Competition anti-corruption gateway (read model)
# ---------------------------------------------------------------------------


@runtime_checkable
class CompetitionCatalog(Protocol):
    """Port: the anti-corruption gateway to the Competition context.

    Translates the foreign Competition configuration into this context's own
    read-model value objects. The application layer calls this before
    :meth:`Submission.submit` and passes the result in, so the domain validates
    admissibility and participant-count rules against a local projection - never by
    importing the Competition aggregate.

    Getters return ``None`` when the referenced competition or combination is
    unknown, leaving the "not found" decision to the use case.
    """

    def exists(self, competition_id: CompetitionId) -> bool:
        """Whether a competition with ``competition_id`` exists."""
        ...

    def accepts_submissions(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        """Whether the competition currently accepts new submissions at ``now``.

        Folds the competition's status and its submission deadlines into a single
        answer, so the use case need not know the Competition's lifecycle model.
        """
        ...

    def participation_policy(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> SubmissionParticipationPolicy | None:
        """Return the participation policy for a combination, or ``None`` if unknown.

        Carries the combination's admissibility and the chosen participant group's
        count band - exactly the slice of Competition configuration the domain
        needs to validate a submission.
        """
        ...

    def price_per_participant(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> Money | None:
        """Return the per-participant price for a combination, or ``None`` if unknown.

        The Competition owns pricing; the use case multiplies this by the
        participant count and freezes the total as an immutable ``PriceSnapshot``.
        """
        ...


# ---------------------------------------------------------------------------
# Organization anti-corruption gateway (read model)
# ---------------------------------------------------------------------------


@runtime_checkable
class OrganizationReadModel(Protocol):
    """Port: the anti-corruption gateway to the Organization (staff) context.

    Answers the two authorization questions the Submission use cases need without
    importing an Organization aggregate: does a user hold staff permission, and is
    a reviewer authorized to act on submissions as an organizer.
    """

    def has_staff_permission(self, *, user_id: UserId) -> bool:
        """Whether ``user_id`` holds an active staff membership (general back-office access)."""
        ...

    def can_review_submissions(self, *, reviewer_id: ReviewerId) -> bool:
        """Whether ``reviewer_id`` is authorized to review/decide submissions as an organizer."""
        ...


# ---------------------------------------------------------------------------
# Identity anti-corruption gateway (read model)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApplicantInfo:
    """A flat projection of an applicant's Identity profile (display data only).

    The Submission context stores only the applicant's :class:`UserId`; when a
    caller needs the applicant's name/email it is resolved through the Identity ACL
    into this read model - the aggregate is never imported.
    """

    user_id: str
    display_name: str
    email: str


@runtime_checkable
class IdentityReadModel(Protocol):
    """Port: the anti-corruption gateway to the Identity (users) context."""

    def exists(self, *, user_id: UserId) -> bool:
        """Whether an Identity user with ``user_id`` exists (applicant precondition)."""
        ...

    def get_applicant(self, *, user_id: UserId) -> ApplicantInfo | None:
        """Return the applicant's display information, or ``None`` if unknown."""
        ...


# ---------------------------------------------------------------------------
# Ambient-dependency ports (time & identity, injected not read globally)
# ---------------------------------------------------------------------------


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, injected rather than read globally."""

    def now(self) -> datetime:
        """The current instant as a timezone-aware datetime (possibly non-UTC)."""
        ...

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware **UTC** datetime."""
        ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: source of fresh UUID v7 identifiers, injected rather than read globally."""

    def new(self) -> uuid.UUID:
        """Return a brand-new time-ordered UUID version 7."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Port: dispatch recorded domain events to the world outside the aggregate."""

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish ``events`` in order to the platform's event transport."""
        ...
