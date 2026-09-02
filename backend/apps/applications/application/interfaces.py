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

from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    ApplicationId,
    CompetitionId,
    CompetitionPriceQuote,
    DisciplineId,
    EducationalOrganizationId,
    Money,
    NominationId,
    ParticipantGroupId,
    ParticipationFormatId,
    PriceCalculationType,
    ReviewerId,
    ServiceId,
    SubmissionId,
    SubmissionParticipationPolicy,
    UserId,
)

__all__ = [
    "AdditionalServiceQuote",
    "ApplicantInfo",
    "ApplicationRepository",
    "Clock",
    "CompetitionCatalog",
    "CompetitionOrganizerDirectory",
    "CompetitionPriceQuote",
    "CompetitionServiceCatalog",
    "CompetitionUploadPolicy",
    "EducationalOrganizationDirectory",
    "EducationalOrganizationInfo",
    "EventPublisher",
    "FileStorage",
    "IdentityReadModel",
    "OrganizationReadModel",
    "OrganizerContacts",
    "OrganizerNotifier",
    "ParticipantGuardianRegistry",
    "PendingRevisions",
    "ReceiptRequirement",
    "RevisionJournal",
    "SubmissionRepository",
    "UploadConstraints",
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

    def accepts_submissions(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId | None = None,
        now: datetime,
    ) -> bool:
        """Whether the competition currently accepts new submissions at ``now``.

        Registration is scheduled per nomination. When ``nomination_id`` is given,
        the answer is scoped to that nomination's window (and early-stop flag); when
        it is ``None`` — an order-level edit or a submission with no performance yet —
        the answer is "does *any* nomination currently accept applications?". Folds
        the Competition's lifecycle so the use case need not know its status model.
        """
        ...

    def accepts_payment(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        """Whether the competition's payment window is still open at ``now``."""
        ...

    def additional_performance_discount_percent(self, *, competition_id: CompetitionId) -> int:
        """Organizer-configured discount percent applied to 2nd+ performances in one application."""
        ...

    def allows_multiple_performances(self, *, competition_id: CompetitionId) -> bool:
        """Whether one application of this competition may carry more than one performance.

        A festival that judges one act per entrant turns this off. Unknown
        competitions answer ``True``: the use case that cares has already refused an
        unknown competition on its own terms, and a missing row must not silently
        become the stricter rule.
        """
        ...

    def accepts_upload(self, *, competition_id: CompetitionId, attachment_kind: str, now: datetime) -> bool:
        """Whether uploads of ``attachment_kind`` are still allowed at ``now``.

        Honours the music-upload and document-upload deadlines; kinds without a
        dedicated deadline follow the application deadline.
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

    def price_quote(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> CompetitionPriceQuote | None:
        """Return the list-price quote for a combination, or ``None`` if unknown.

        The Competition owns pricing and calculation type; the use case turns the
        quote into a total (per participant or fixed per performance) and freezes
        it as an immutable ``PriceSnapshot``.
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


@runtime_checkable
class ApplicantNotifier(Protocol):
    """Port: telling an applicant what happened to their order.

    Every method carries ``user_id`` as well as ``email`` because a notice reaches
    the applicant by more than one channel: a letter, which can be filtered, missed
    or sent to an address they no longer read, and their cabinet, which is where they
    look when the letter did not arrive. Which channels an adapter actually uses is
    its own business; the use case states the fact once.
    """

    def notify_application_submitted(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        """The order was submitted with a payment receipt already attached."""
        ...

    def notify_application_awaiting_payment(self, *, user_id: str, email: str, applicant_name: str, application_id: str, deadline: datetime) -> None:
        """The order was submitted without a receipt; payment is expected by ``deadline``."""
        ...

    def notify_application_auto_cancelled(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        """The order was auto-cancelled because no receipt was attached in time."""
        ...


# ---------------------------------------------------------------------------
# Post-submission revisions: journal, organizer directory, organizer notifier
# ---------------------------------------------------------------------------
#
# An order stays editable after it is placed (registration is still open, or the
# organizer asked for corrections). The organizer has already read it, so a silent
# change is the one thing that must not happen - but a letter per keystroke is not a
# notification, it is noise. The three ports below carry the compromise: edits are
# journalled as they happen, and a periodic sweep folds each order's pending edits
# into one letter.


@dataclass(frozen=True, slots=True)
class PendingRevisions:
    """Every not-yet-reported edit to one submitted order, folded into one digest."""

    application_id: str
    competition_id: str
    applicant_id: str
    #: The recorded change descriptions, oldest first, ready to list in a letter.
    changes: tuple[str, ...]
    first_at: datetime
    last_at: datetime


@runtime_checkable
class RevisionJournal(Protocol):
    """Port: the append-only record of edits made to orders after they were placed."""

    def pending(self, *, quiet_since: datetime) -> Sequence[PendingRevisions]:
        """Return the orders whose edits are unreported and have settled down.

        ``quiet_since`` is the cut-off the *newest* pending edit must predate. An
        applicant working through a form produces a change every few seconds; the
        quiet period is what turns that stream into a single digest instead of a
        digest per pause.
        """
        ...

    def mark_notified(self, *, application_id: str, up_to: datetime, now: datetime) -> None:
        """Stamp every pending edit of ``application_id`` recorded up to ``up_to`` as reported.

        Bounded by ``up_to`` rather than "all pending", so an edit made while the
        digest was being sent is carried into the next one instead of being lost.
        """
        ...


@dataclass(frozen=True, slots=True)
class OrganizerContacts:
    """Where to write to reach the people running a competition."""

    competition_title: str
    emails: tuple[str, ...]


@runtime_checkable
class CompetitionOrganizerDirectory(Protocol):
    """Port: the ACL resolving a competition to its organizer's mailboxes."""

    def get_organizer(self, *, competition_id: CompetitionId) -> OrganizerContacts | None:
        """Return the competition's title and organizer mailboxes, or ``None`` if unknown.

        ``None`` and "known competition with no mailbox on file" are different
        answers, and the caller treats both as "nobody to tell" - but only the
        second is a configuration gap worth logging.
        """
        ...


@runtime_checkable
class OrganizerNotifier(Protocol):
    """Port: transactional emails sent to an organizer about an applicant's actions."""

    def notify_application_revised(
        self,
        *,
        emails: Sequence[str],
        competition_title: str,
        applicant_name: str,
        application_id: str,
        changes: Sequence[str],
        revised_at: datetime,
    ) -> None:
        """An already-submitted order was edited; ``changes`` is what the applicant did."""
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


# ---------------------------------------------------------------------------
# Application (order) repository port
# ---------------------------------------------------------------------------


@runtime_checkable
class ApplicationRepository(Protocol):
    """Port: persistence & retrieval of the :class:`Application` aggregate.

    Loads and saves the whole order aggregate (its submission references, service
    lines, consents, total price and status history) as one unit, honouring the
    root's optimistic-concurrency ``version``. It never loads the referenced
    Submissions - those are a separate aggregate reached through
    :class:`SubmissionRepository`.
    """

    def get(self, application_id: ApplicationId) -> Application | None:
        """Return the application with ``application_id``, or ``None``."""
        ...

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Application]:
        """Return all non-deleted applications owned by ``applicant_id`` (newest first)."""
        ...

    def save(self, application: Application) -> None:
        """Persist ``application`` and its whole graph (insert or update), honouring its version."""
        ...


# ---------------------------------------------------------------------------
# Competition additional-service & consent gateway (read model / ACL)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdditionalServiceQuote:
    """A Competition additional service projected into this context.

    Carries the full organizer configuration the order needs: the unit price, how it
    is billed (``billing_model``), the participation formats it is scoped to
    (``available_format_ids``) and whether it is mandatory (``required``).
    """

    service_id: ServiceId
    name: str
    unit_price: Money
    billing_model: PriceCalculationType = PriceCalculationType.PER_PARTICIPANT
    available_format_ids: frozenset[str] = frozenset()
    required: bool = False


@dataclass(frozen=True, slots=True)
class ReceiptRequirement:
    """Whether the order must carry a payment receipt, and by which moment.

    Two organizer settings collapse into this pair. ``required`` mirrors the
    format's ``require_receipt``; ``due_at_submit`` is the answer to its
    ``allow_upload_later`` — when uploading later is *not* permitted, the receipt
    has to be attached before the order may be placed, otherwise it is only owed
    before the order can be marked paid.
    """

    required: bool = False
    due_at_submit: bool = False

    @classmethod
    def none(cls) -> ReceiptRequirement:
        """No receipt is required at all."""
        return cls()


@runtime_checkable
class CompetitionServiceCatalog(Protocol):
    """Port: the Competition ACL for additional services and required consents.

    Segregated from :class:`CompetitionCatalog` (which serves the per-submission
    pricing/policy the domain validates against) so the two evolve independently.
    Both are backed by the same Competition context at composition time.
    """

    def get_additional_service(self, *, competition_id: CompetitionId, service_id: ServiceId) -> AdditionalServiceQuote | None:
        """Return the competition's additional service (name + unit price), or ``None`` if unknown."""
        ...

    def required_consent_codes(self, *, competition_id: CompetitionId) -> frozenset[str]:
        """Return the consent codes the competition requires before an application may be submitted."""
        ...

    def required_service_ids(self, *, competition_id: CompetitionId, participation_format_ids: frozenset[str]) -> frozenset[str]:
        """Return the ids of services the competition mandates for the given formats.

        A service is required when it is enabled, marked ``required``, and available
        for at least one of the order's chosen participation formats.
        """
        ...

    def receipt_requirement(
        self,
        *,
        competition_id: CompetitionId,
        participation_format_ids: frozenset[str],
    ) -> ReceiptRequirement:
        """Return whether a payment receipt is mandatory for this order, and when.

        The requirement is configured per participation format, and one order may
        span several — so the strictest wins: the receipt is required if *any*
        chosen format requires it, and it is due at submit unless *every* format
        requiring it also permits uploading later.
        """
        ...


# ---------------------------------------------------------------------------
# Educational-organization directory gateway (read model / ACL)
# ---------------------------------------------------------------------------


@runtime_checkable
class ParticipantGuardianRegistry(Protocol):
    """Port: the Participants ACL answering who has a verified guardian on file.

    A competition may insist that every performer be backed by a parent or legal
    guardian. The relationship itself belongs to the Participants context (it long
    outlives any one application), so this context only asks the question and never
    models the link.
    """

    def participants_without_active_guardian(self, *, participant_ids: frozenset[str]) -> frozenset[str]:
        """Return the subset of ids that have no *active* guardian relationship.

        A merely proposed link does not count — an unverified claim of guardianship
        is exactly what the requirement exists to catch. Unknown ids are reported as
        missing rather than silently passing.
        """
        ...


@dataclass(frozen=True, slots=True)
class EducationalOrganizationInfo:
    """A flat projection of an educational organization (id + display name)."""

    organization_id: str
    name: str


@runtime_checkable
class EducationalOrganizationDirectory(Protocol):
    """Port: the Institutions ACL resolving an educational-organization reference to its name."""

    def get(self, *, organization_id: EducationalOrganizationId) -> EducationalOrganizationInfo | None:
        """Return the organization's display info, or ``None`` if unknown."""
        ...


# ---------------------------------------------------------------------------
# File storage & upload-policy ports (attachments)
# ---------------------------------------------------------------------------


@runtime_checkable
class FileStorage(Protocol):
    """Port: durable storage for uploaded attachment bytes.

    The application layer hands over raw bytes and receives back an opaque storage
    reference (a key/URL) to persist on the aggregate as a
    :class:`~apps.applications.domain.value_objects.FileReference`. Reading the bytes
    back is a delivery concern outside this port.
    """

    def save(self, *, content: bytes, filename: str, content_type: str) -> str:
        """Store ``content`` and return the opaque storage reference."""
        ...

    def delete(self, *, reference: str) -> None:
        """Delete the stored object at ``reference`` (best-effort)."""
        ...


@dataclass(frozen=True, slots=True)
class UploadConstraints:
    """The validation limits for one kind of upload.

    ``max_bytes`` bounds the single file being uploaded. ``shared_budget_kinds`` names the
    kinds whose sizes are counted **together** against it — media is configured as one
    ceiling over a performance's photographs *and* video, because several files are the
    normal case and a per-file limit either waves ten of them through or refuses one
    legitimate one. Empty means the limit is per file, which is how music and documents
    work.
    """

    max_bytes: int
    allowed_extensions: frozenset[str]
    shared_budget_kinds: frozenset[str] = frozenset()

    def allows_extension(self, extension: str) -> bool:
        """Whether ``extension`` (lower-case, no dot) is permitted."""
        return extension.lower().lstrip(".") in self.allowed_extensions


@runtime_checkable
class CompetitionUploadPolicy(Protocol):
    """Port: the Competition ACL for attachment upload limits.

    Projects the competition's media settings (music formats/size, document rules)
    into the constraints an upload must satisfy, so validation reuses the
    competition's configuration rather than hard-coding limits at the edge.
    """

    def limits_for(self, *, competition_id: CompetitionId, attachment_kind: str, participation_format_id: str | None = None) -> UploadConstraints:
        """Return the upload constraints for ``attachment_kind`` in this competition.

        When ``participation_format_id`` is given, the constraints reflect that
        format's configured requirements (e.g. the organizer's allowed audio formats
        and maximum music size); otherwise the platform defaults apply.
        """
        ...
