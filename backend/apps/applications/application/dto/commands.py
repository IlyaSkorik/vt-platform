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
    "CancelSubmissionCommand",
    "CreateSubmissionCommand",
    "DeleteDraftSubmissionCommand",
    "MarkPaidCommand",
    "MarkWaitingPaymentCommand",
    "RemoveAttachmentCommand",
    "RemoveParticipantCommand",
    "RemoveTeacherCommand",
    "ReturnSubmissionForCorrectionCommand",
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
    """Set the submission's single performance (owner, editable states only)."""

    submission_id: str
    requested_by: str
    title: str
    duration_seconds: int
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str


@dataclass(frozen=True, slots=True)
class UpdatePerformanceCommand:
    """Replace the submission's existing performance (owner, editable states only)."""

    submission_id: str
    requested_by: str
    title: str
    duration_seconds: int
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddParticipantCommand:
    """Add a participant to the submission (owner, editable states only)."""

    submission_id: str
    requested_by: str
    first_name: str
    last_name: str
    birth_date: str
    gender: str
    middle_name: str | None = None


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
