"""Domain exceptions for the Applications (Competition Submission) bounded context.

Typed, framework-free domain errors raised by the domain (entities, value
objects) and mapped to RFC 9457 Problem Details at the presentation edge
(ARCH-001 §7.6). No Django/DRF imports.

    SubmissionDomainError                       - base for every error in this context
    ├── ValueObjectValidationError              - a value object rejected its input
    │   ├── InvalidSubmissionIdError
    │   ├── InvalidParticipantIdError
    │   ├── InvalidTeacherIdError
    │   ├── InvalidAttachmentIdError
    │   ├── InvalidReviewIdError
    │   ├── InvalidCompetitionIdError
    │   ├── InvalidUserIdError
    │   ├── InvalidReviewerIdError
    │   ├── InvalidNominationIdError
    │   ├── InvalidDisciplineIdError
    │   ├── InvalidAgeCategoryIdError
    │   ├── InvalidParticipantGroupIdError
    │   ├── InvalidParticipationFormatIdError
    │   ├── InvalidPerformanceTitleError
    │   ├── InvalidDurationError
    │   ├── InvalidPersonNameError
    │   ├── InvalidBirthDateError
    │   ├── InvalidTeacherRoleError
    │   ├── InvalidFileReferenceError
    │   ├── InvalidReviewCommentError
    │   ├── InvalidMoneyError
    │   ├── InvalidPriceSnapshotError
    │   └── InvalidParticipantCountRangeError
    ├── DirectConstructionError                 - an aggregate was built bypassing its factories
    ├── SubmissionStateError                    - an operation illegal in the Submission's lifecycle
    │   ├── SubmissionNotEditableError          - content edited when the submission is not editable
    │   ├── IllegalStatusTransitionError        - the requested lifecycle transition is not legal
    │   └── PriceSnapshotLockedError            - the price snapshot was changed after it froze
    ├── SubmissionReferenceError                - a referenced child does not exist in the submission
    │   ├── ParticipantNotFoundError
    │   ├── TeacherNotFoundError
    │   └── AttachmentNotFoundError
    ├── SubmissionConflictError                 - a child would duplicate one already present
    │   ├── DuplicateParticipantError
    │   └── DuplicateAttachmentError
    └── SubmissionInvariantError                - an aggregate invariant would be violated
        ├── PerformanceRequiredError
        ├── ParticipantRequiredError
        ├── PriceSnapshotRequiredError
        ├── CannotRemoveLastParticipantError
        ├── CombinationNotAdmissibleError
        └── ParticipantCountMismatchError
"""

from __future__ import annotations


class SubmissionDomainError(Exception):
    """Base class for all errors raised by the Applications domain."""


# ---------------------------------------------------------------------------
# Value-object validation
# ---------------------------------------------------------------------------


class ValueObjectValidationError(SubmissionDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so callers treating construction like value
    parsing keep working, while still being catchable as a domain-specific error.
    """


class InvalidSubmissionIdError(ValueObjectValidationError):
    """The provided value is not a valid ``SubmissionId`` (must be a UUID v7)."""


class InvalidParticipantIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ParticipantId`` (must be a UUID v7)."""


class InvalidTeacherIdError(ValueObjectValidationError):
    """The provided value is not a valid ``TeacherId`` (must be a UUID v7)."""


class InvalidAttachmentIdError(ValueObjectValidationError):
    """The provided value is not a valid ``AttachmentId`` (must be a UUID v7)."""


class InvalidReviewIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ReviewId`` (must be a UUID v7)."""


class InvalidCompetitionIdError(ValueObjectValidationError):
    """The provided value is not a valid ``CompetitionId`` reference (must be a UUID v7)."""


class InvalidUserIdError(ValueObjectValidationError):
    """The provided value is not a valid ``UserId`` reference (must be a UUID v7)."""


class InvalidReviewerIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ReviewerId`` reference (must be a UUID v7)."""


class InvalidNominationIdError(ValueObjectValidationError):
    """The provided value is not a valid ``NominationId`` reference (must be a UUID v7)."""


class InvalidDisciplineIdError(ValueObjectValidationError):
    """The provided value is not a valid ``DisciplineId`` reference (must be a UUID v7)."""


class InvalidAgeCategoryIdError(ValueObjectValidationError):
    """The provided value is not a valid ``AgeCategoryId`` reference (must be a UUID v7)."""


class InvalidParticipantGroupIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ParticipantGroupId`` reference (must be a UUID v7)."""


class InvalidParticipationFormatIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ParticipationFormatId`` reference (must be a UUID v7)."""


class InvalidPerformanceTitleError(ValueObjectValidationError):
    """The provided value is not a valid performance title (empty or too long)."""


class InvalidDurationError(ValueObjectValidationError):
    """The provided value is not a valid duration (non-positive or implausibly long)."""


class InvalidPersonNameError(ValueObjectValidationError):
    """The provided value is not a valid person name (empty parts or over-long fields)."""


class InvalidBirthDateError(ValueObjectValidationError):
    """The provided value is not a valid birth date (not a date, out of bounds, or in the future)."""


class InvalidTeacherRoleError(ValueObjectValidationError):
    """The provided value is not a valid teacher role (empty or too long)."""


class InvalidFileReferenceError(ValueObjectValidationError):
    """The provided value is not a valid file reference (empty or too long)."""


class InvalidReviewCommentError(ValueObjectValidationError):
    """The provided value is not a valid review comment (empty or too long)."""


class InvalidMoneyError(ValueObjectValidationError):
    """The provided value is not a valid monetary amount (negative or malformed)."""


class InvalidPriceSnapshotError(ValueObjectValidationError):
    """The provided value is not a valid price snapshot (missing price or timestamp)."""


class InvalidParticipantCountRangeError(ValueObjectValidationError):
    """The provided counts do not form a valid participant-count range."""


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class DirectConstructionError(SubmissionDomainError):
    """Raised when an aggregate is built directly instead of via its factories.

    The :class:`~apps.applications.domain.entities.Submission` aggregate root must
    be created through its ``draft`` factory (a new instance) or ``rehydrate``
    (reconstruction from persistence), which alone establish the creation
    invariants. Calling the dataclass constructor directly bypasses them and is
    refused.
    """


# ---------------------------------------------------------------------------
# Lifecycle state
# ---------------------------------------------------------------------------


class SubmissionStateError(SubmissionDomainError):
    """Base for an operation illegal in the ``Submission`` aggregate's lifecycle state."""


class SubmissionNotEditableError(SubmissionStateError):
    """Content was edited while the submission is not editable.

    A submission's content (performance, participants, teachers, attachments,
    price snapshot) is mutable only while ``DRAFT`` or ``REQUIRES_CORRECTION``.
    Once submitted for review - and certainly once ``ACCEPTED`` - it is frozen so
    that a decision already resting on it cannot be invalidated underneath it.
    """


class IllegalStatusTransitionError(SubmissionStateError):
    """The requested lifecycle transition is not legal from the current status."""


class PriceSnapshotLockedError(SubmissionStateError):
    """The immutable price snapshot was changed after it was frozen.

    Once a submission leaves the editable states the snapshot is permanent: future
    Competition pricing changes must never alter the price of an existing
    submission.
    """


# ---------------------------------------------------------------------------
# Referential integrity within the aggregate
# ---------------------------------------------------------------------------


class SubmissionReferenceError(SubmissionDomainError):
    """Base: an operation references a child that does not exist in this submission."""


class ParticipantNotFoundError(SubmissionReferenceError):
    """The referenced participant does not exist in this submission."""


class TeacherNotFoundError(SubmissionReferenceError):
    """The referenced teacher does not exist in this submission."""


class AttachmentNotFoundError(SubmissionReferenceError):
    """The referenced attachment does not exist in this submission."""


# ---------------------------------------------------------------------------
# Uniqueness conflicts
# ---------------------------------------------------------------------------


class SubmissionConflictError(SubmissionDomainError):
    """Base: a child would duplicate one that already exists in this submission."""


class DuplicateParticipantError(SubmissionConflictError):
    """A participant with the same name and birth date is already in this submission."""


class DuplicateAttachmentError(SubmissionConflictError):
    """An attachment referencing the same file is already in this submission."""


# ---------------------------------------------------------------------------
# Aggregate invariants
# ---------------------------------------------------------------------------


class SubmissionInvariantError(SubmissionDomainError):
    """Base: an operation would leave the aggregate in an invalid state."""


class PerformanceRequiredError(SubmissionInvariantError):
    """The submission has no performance and cannot be submitted."""


class ParticipantRequiredError(SubmissionInvariantError):
    """The submission has no participants and cannot be submitted."""


class PriceSnapshotRequiredError(SubmissionInvariantError):
    """The submission has no immutable price snapshot and cannot be submitted."""


class CannotRemoveLastParticipantError(SubmissionInvariantError):
    """Removing the only remaining participant is not allowed."""


class CombinationNotAdmissibleError(SubmissionInvariantError):
    """The performance's configuration combination is not admissible in the competition."""


class ParticipantCountMismatchError(SubmissionInvariantError):
    """The participant count does not match the configured participant group's range."""
