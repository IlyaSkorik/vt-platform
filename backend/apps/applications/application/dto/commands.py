"""Command DTOs for the Applications (Competition Submission) bounded context.

Input shapes for state-changing use cases. Framework-neutral, frozen, slotted
dataclasses carrying only primitives - no domain value objects (handlers build
those, translating validation errors) and no framework types. Ids and enums are
carried as strings; the acting identity travels on every command (``applicant_id``
/ ``requested_by`` for the owner, ``reviewer_id`` for an organizer) so the use case
can enforce ownership and permission.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AcceptSubmissionCommand",
    "AddParticipantCommand",
    "AddTeacherCommand",
    "ApproveSubmissionCommand",
    "AttachFileCommand",
    "CalculatePriceCommand",
    "CancelSubmissionByReviewerCommand",
    "CancelSubmissionCommand",
    "CompleteSubmissionCommand",
    "CreateSubmissionCommand",
    "DeleteDraftSubmissionCommand",
    "MarkPaidCommand",
    "MarkWaitingPaymentCommand",
    "RemoveAttachmentCommand",
    "RemoveParticipantCommand",
    "RemoveTeacherCommand",
    "ReturnSubmissionForCorrectionCommand",
    "ScheduleSubmissionCommand",
    "SetParticipantMemberCountCommand",
    "SetParticipantMembersCommand",
    "SetPerformanceCommand",
    "StartReviewCommand",
    "SubmitSubmissionCommand",
    "UpdateParticipantCommand",
    "UpdatePerformanceCommand",
    "UpdateTeacherCommand",
    "UploadAttachmentCommand",
]


# ---------------------------------------------------------------------------
# Draft lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateSubmissionCommand:
    """Create a new DRAFT submission for a competition, owned by the applicant."""

    competition_id: str
    applicant_id: str


@dataclass(frozen=True, slots=True)
class DeleteDraftSubmissionCommand:
    """Delete a draft submission (owner only; only a DRAFT may be deleted)."""

    submission_id: str
    requested_by: str


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SetPerformanceCommand:
    """Set the submission's single performance (owner, editable states only).

    ``comment`` is the applicant's optional note for the organizers about this act;
    ``age_composition`` is what ages the performers are, asked for by a mixed age
    category and empty for a standard one.
    """

    submission_id: str
    requested_by: str
    title: str
    duration_seconds: int
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str
    comment: str = ""
    age_composition: str = ""


@dataclass(frozen=True, slots=True)
class UpdatePerformanceCommand:
    """Replace the submission's existing performance (owner, editable states only).

    ``comment`` is the applicant's optional note for the organizers about this act;
    ``age_composition`` is what ages the performers are, asked for by a mixed age
    category and empty for a standard one.
    """

    submission_id: str
    requested_by: str
    title: str
    duration_seconds: int
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str
    comment: str = ""
    age_composition: str = ""


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddParticipantCommand:
    """Add a participant to the submission (owner, editable states only).

    Normally a Participant Registry entry is selected: ``registry_participant_id``
    links it and the name/birth-date/gender are its snapshot. A collective carries
    only ``display_name`` plus a ``member_count`` (its headcount). All person fields
    are optional so both solo and collective registry participants (and a manual
    entry) are expressible. ``member_count`` is 1 for a solo, the number of people
    for a collective; it drives the count-band check and per-participant pricing.
    """

    submission_id: str
    requested_by: str
    first_name: str | None = None
    last_name: str | None = None
    birth_date: str | None = None
    gender: str | None = None
    middle_name: str | None = None
    display_name: str | None = None
    registry_participant_id: str | None = None
    member_count: int = 1


@dataclass(frozen=True, slots=True)
class UpdateParticipantCommand:
    """Replace a participant's details (owner, editable states only).

    The domain models participants as add/remove only, so an update replaces the
    identified participant with a fresh one carrying the new details (a new
    ``ParticipantId``).
    """

    submission_id: str
    requested_by: str
    participant_id: str
    first_name: str
    last_name: str
    birth_date: str
    gender: str
    middle_name: str | None = None


@dataclass(frozen=True, slots=True)
class SetParticipantMemberCountCommand:
    """Correct a collective entry's headcount (owner, editable states only).

    Its own command rather than a variant of "update participant": that one replaces
    the entry with a fresh id and would take the roster with it. How many people are
    on stage is a correction to the entry, not a different entry.
    """

    submission_id: str
    requested_by: str
    participant_id: str
    member_count: int


@dataclass(frozen=True, slots=True)
class SetParticipantMembersCommand:
    """Name the people in a collective (owner, editable states only).

    The whole roster, replacing whatever was there — an empty list withdraws the
    request. Naming the people *is* the request for an individual document each, so
    there is no separate opt-in flag to keep in step with it.
    """

    submission_id: str
    requested_by: str
    participant_id: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RemoveParticipantCommand:
    """Remove a participant from the submission (owner; not the last one)."""

    submission_id: str
    requested_by: str
    participant_id: str


# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddTeacherCommand:
    """Add a teacher in a configurable role (owner, editable states only)."""

    submission_id: str
    requested_by: str
    first_name: str
    last_name: str
    role: str
    middle_name: str | None = None
    directory_teacher_id: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTeacherCommand:
    """Replace a teacher's details (owner, editable states only).

    Like participants, an update replaces the identified teacher with a fresh one
    (a new ``TeacherId``).
    """

    submission_id: str
    requested_by: str
    teacher_id: str
    first_name: str
    last_name: str
    role: str
    middle_name: str | None = None


@dataclass(frozen=True, slots=True)
class RemoveTeacherCommand:
    """Remove a teacher from the submission (owner)."""

    submission_id: str
    requested_by: str
    teacher_id: str


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AttachFileCommand:
    """Attach a file reference to the submission (owner, editable states only)."""

    submission_id: str
    requested_by: str
    attachment_type: str
    file_reference: str
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class RemoveAttachmentCommand:
    """Remove an attachment reference from the submission (owner)."""

    submission_id: str
    requested_by: str
    attachment_id: str


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalculatePriceCommand:
    """Calculate and freeze the submission's immutable price snapshot (owner).

    Prices the performance combination through the Competition catalog and
    multiplies the per-participant price by the current participant count.
    """

    submission_id: str
    requested_by: str


# ---------------------------------------------------------------------------
# Submission & review lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubmitSubmissionCommand:
    """Submit the submission to the competition (owner)."""

    submission_id: str
    requested_by: str


@dataclass(frozen=True, slots=True)
class StartReviewCommand:
    """Begin reviewing a submitted submission (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class ReturnSubmissionForCorrectionCommand:
    """Return the submission to the applicant for correction, with a mandatory comment (organizer)."""

    submission_id: str
    reviewer_id: str
    comment: str


@dataclass(frozen=True, slots=True)
class ApproveSubmissionCommand:
    """Approve the submission under review (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class CancelSubmissionCommand:
    """Cancel (withdraw) the submission (owner); not possible once accepted."""

    submission_id: str
    requested_by: str


# ---------------------------------------------------------------------------
# Payment & acceptance lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkWaitingPaymentCommand:
    """Move the approved submission to awaiting payment (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class MarkPaidCommand:
    """Mark the submission's fee as paid (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class AcceptSubmissionCommand:
    """Accept the paid submission into the competition (organizer); content then freezes."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class ScheduleSubmissionCommand:
    """Move an accepted submission into running competition (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class CompleteSubmissionCommand:
    """Mark a running submission as completed (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class CancelSubmissionByReviewerCommand:
    """Cancel a submission by organizer decision (organizer)."""

    submission_id: str
    reviewer_id: str


@dataclass(frozen=True, slots=True)
class UploadAttachmentCommand:
    """Upload and attach a file to the submission (owner, editable states only).

    Carries the raw uploaded bytes plus its declared filename and content type; the
    handler validates them against the competition's upload constraints, stores the
    bytes, and attaches the resulting reference.
    """

    submission_id: str
    requested_by: str
    attachment_type: str
    filename: str
    content_type: str
    content: bytes
    caption: str | None = None
