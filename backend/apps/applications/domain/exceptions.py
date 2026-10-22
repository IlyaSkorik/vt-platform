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
    │   ├── InvalidPerformanceCommentError
    │   ├── InvalidAgeCompositionError
    │   ├── InvalidDurationError
    │   ├── InvalidPersonNameError
    │   ├── InvalidBirthDateError
    │   ├── InvalidParticipantMemberCountError
    │   ├── InvalidCollectiveMemberError
    │   ├── InvalidTeacherRoleError
    │   ├── InvalidFileReferenceError
    │   ├── InvalidReviewCommentError
    │   ├── InvalidMoneyError
    │   ├── InvalidPriceSnapshotError
    │   ├── InvalidPaymentReceiptError
    │   ├── InvalidPaymentReceiptIdError
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
        ├── TeacherRequiredError
        ├── ParticipantCommentNotAcceptedError
        ├── RequiredAttachmentMissingError
        ├── AgeCompositionRequiredError
        ├── PriceSnapshotRequiredError
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


class InvalidRegistryParticipantIdError(ValueObjectValidationError):
    """The provided value is not a valid ``RegistryParticipantId`` reference (must be a UUID v7)."""


class InvalidTeacherIdError(ValueObjectValidationError):
    """The provided value is not a valid ``TeacherId`` (must be a UUID v7)."""


class InvalidDirectoryTeacherIdError(ValueObjectValidationError):
    """The provided value is not a valid ``DirectoryTeacherId`` reference (must be a UUID v7)."""


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


class InvalidPerformanceCommentError(ValueObjectValidationError):
    """The provided value is not a valid performance comment (too long)."""


class InvalidAgeCompositionError(ValueObjectValidationError):
    """The provided value is not a valid description of the group's ages (too long)."""


class InvalidDurationError(ValueObjectValidationError):
    """The provided value is not a valid duration (non-positive or implausibly long)."""


class InvalidPersonNameError(ValueObjectValidationError):
    """The provided value is not a valid person name (empty parts or over-long fields)."""


class InvalidBirthDateError(ValueObjectValidationError):
    """The provided value is not a valid birth date (not a date, out of bounds, or in the future)."""


class InvalidParticipantMemberCountError(ValueObjectValidationError):
    """The provided participant member count is not a valid headcount (not an integer >= 1)."""


class InvalidCollectiveMemberError(ValueObjectValidationError):
    """The provided collective roster is not usable (a name too long, or too many names)."""


class InvalidParticipantOrganizationError(ValueObjectValidationError):
    """The provided institution name is not usable (too long to print)."""


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


class InvalidPaymentReceiptError(ValueObjectValidationError):
    """The provided value is not a valid payment receipt (missing id, file reference or timestamp)."""


class InvalidPaymentReceiptIdError(ValueObjectValidationError):
    """The provided value is not a valid ``PaymentReceiptId`` (must be a UUID v7)."""


class InvalidParticipantCountRangeError(ValueObjectValidationError):
    """The provided counts do not form a valid participant-count range."""


class InvalidSubmissionStatusChangeError(ValueObjectValidationError):
    """The provided value is not a valid submission status-history entry."""


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


class TeacherRequiredError(SubmissionInvariantError):
    """The competition requires a teacher, but the submission credits none."""


class ParticipantCommentNotAcceptedError(SubmissionInvariantError):
    """The competition does not invite a participant comment, but one is present."""


class RequiredAttachmentMissingError(SubmissionInvariantError):
    """A file the competition requires for this format (music/video/receipt) is missing."""


class AgeCompositionRequiredError(SubmissionInvariantError):
    """A mixed age category was chosen without saying what ages the group actually is."""


class PriceSnapshotRequiredError(SubmissionInvariantError):
    """The submission has no immutable price snapshot and cannot be submitted."""


class CombinationNotAdmissibleError(SubmissionInvariantError):
    """The performance's configuration combination is not admissible in the competition."""


class ParticipantCountMismatchError(SubmissionInvariantError):
    """The participant count does not match the configured participant group's range."""


# ===========================================================================
# Application aggregate (order-level) errors
# ===========================================================================
#
# The Application is the *order* aggregate: it references its Submissions by id
# (never contains them) and owns the educational organization, additional
# services, consents, total price snapshot and payment state. Its error tree is
# kept independent of the Submission tree above so the two aggregates stay
# decoupled even though they share this bounded context.
#
#     ApplicationDomainError                          - base for every Application error
#     ├── ApplicationValueError                       - an Application value object rejected its input
#     │   ├── InvalidApplicationIdError
#     │   ├── InvalidEducationalOrganizationIdError
#     │   ├── InvalidServiceIdError
#     │   ├── InvalidOrganizationNameError
#     │   ├── InvalidServiceLineError
#     │   ├── InvalidConsentError
#     │   ├── InvalidSubmissionRefError
#     │   ├── InvalidTotalPriceSnapshotError
#     │   └── InvalidApplicationStatusChangeError
#     ├── DirectApplicationConstructionError          - the root was built bypassing its factories
#     ├── ApplicationStateError                       - an operation illegal in the order lifecycle
#     │   ├── ApplicationNotEditableError
#     │   ├── IllegalApplicationStatusTransitionError
#     │   ├── PaymentReceiptNotAllowedError
#     │   ├── TooManyPaymentReceiptsError
#     │   └── TotalPriceLockedError
#     ├── ApplicationReferenceError                   - a referenced line/ref is absent
#     │   ├── SubmissionRefNotFoundError
#     │   ├── PaymentReceiptNotFoundError
#     │   └── ServiceLineNotFoundError
#     ├── ApplicationConflictError                    - a line/ref would duplicate one present
#     │   ├── DuplicateSubmissionRefError
#     │   └── DuplicateServiceLineError
#     └── ApplicationInvariantError                   - an order invariant would be violated
#         ├── NoSubmissionsError
#         ├── MissingRequiredConsentError
#         └── NotAllSubmissionsApprovedError


class ApplicationDomainError(Exception):
    """Base class for all errors raised by the Application (order) aggregate."""


class ApplicationValueError(ApplicationDomainError, ValueError):
    """Raised when an Application value object is constructed from invalid input.

    Subclasses :class:`ValueError` so callers treating construction like value
    parsing keep working, while still being catchable as a domain-specific error.
    """


class InvalidApplicationIdError(ApplicationValueError):
    """The provided value is not a valid ``ApplicationId`` (must be a UUID v7)."""


class InvalidEducationalOrganizationIdError(ApplicationValueError):
    """The provided value is not a valid ``EducationalOrganizationId`` reference (must be a UUID v7)."""


class InvalidServiceIdError(ApplicationValueError):
    """The provided value is not a valid ``ServiceId`` reference (must be a UUID v7)."""


class InvalidOrganizationNameError(ApplicationValueError):
    """The provided value is not a valid educational-organization name (empty or too long)."""


class InvalidServiceLineError(ApplicationValueError):
    """The provided value is not a valid additional-service line (bad quantity or currency mismatch)."""


class InvalidConsentError(ApplicationValueError):
    """The provided value is not a valid consent record (empty code/version or too long)."""


class InvalidSubmissionRefError(ApplicationValueError):
    """The provided value is not a valid submission reference (over-long display fields)."""


class InvalidTotalPriceSnapshotError(ApplicationValueError):
    """The provided value is not a valid total price snapshot (missing/ mismatched money)."""


class InvalidApplicationStatusChangeError(ApplicationValueError):
    """The provided value is not a valid application status-history entry."""


class DirectApplicationConstructionError(ApplicationDomainError):
    """Raised when the Application root is built directly instead of via its factories.

    The :class:`~apps.applications.domain.entities.Application` aggregate root must
    be created through its ``create`` factory (a new instance) or ``rehydrate``
    (reconstruction from persistence). Calling the dataclass constructor directly
    bypasses the creation invariants and is refused.
    """


class ApplicationStateError(ApplicationDomainError):
    """Base for an operation illegal in the ``Application`` aggregate's lifecycle state."""


class ApplicationNotEditableError(ApplicationStateError):
    """Content was edited while the application is not editable.

    An application's content (educational organization, submission references,
    additional services, consents) is mutable only while ``DRAFT``. Once it is
    ``SUBMITTED`` the composition is frozen; per-performance corrections happen on
    the individual Submissions, never by reopening the order.
    """


class IllegalApplicationStatusTransitionError(ApplicationStateError):
    """The requested order-lifecycle transition is not legal from the current status."""


class PaymentReceiptNotAllowedError(ApplicationStateError):
    """A payment receipt was attached (or detached) after the order was already settled.

    A receipt is proof of payment for the order and the set of them may be changed
    any time before it settles (while ``DRAFT``, ``SUBMITTED`` or
    ``WAITING_PAYMENT``); once the order is ``PAID``, ``COMPLETED`` or ``CANCELLED``
    it is final.
    """


class TooManyPaymentReceiptsError(ApplicationStateError):
    """The order already carries as many payment receipts as it may hold.

    An order is often settled by several transfers, so several receipts are normal;
    an unbounded pile of them is not, and is far more likely a client retry loop
    than an applicant paying in that many instalments.
    """


class TotalPriceLockedError(ApplicationStateError):
    """The total price snapshot was changed after the application left ``DRAFT``.

    Once an application is submitted the total is permanent: future Competition
    pricing changes must never alter the price of an application already placed.
    """


class ApplicationReferenceError(ApplicationDomainError):
    """Base: an operation references a line/ref that does not exist in this application."""


class SubmissionRefNotFoundError(ApplicationReferenceError):
    """The referenced submission is not attached to this application."""


class PaymentReceiptNotFoundError(ApplicationReferenceError):
    """The referenced payment receipt is not attached to this application."""


class ServiceLineNotFoundError(ApplicationReferenceError):
    """The referenced additional-service line is not selected on this application."""


class ApplicationConflictError(ApplicationDomainError):
    """Base: a line/ref would duplicate one already present on this application."""


class DuplicateSubmissionRefError(ApplicationConflictError):
    """The submission is already attached to this application."""


class DuplicateServiceLineError(ApplicationConflictError):
    """The additional service is already selected on this application."""


class ApplicationInvariantError(ApplicationDomainError):
    """Base: an operation would leave the application in an invalid state."""


class NoSubmissionsError(ApplicationInvariantError):
    """The application references no submissions and cannot be submitted."""


class MissingRequiredConsentError(ApplicationInvariantError):
    """A consent the competition requires has not been recorded on the application."""


class MissingRequiredServiceError(ApplicationInvariantError):
    """An additional service the competition mandates has not been selected."""


class PayerRequiredError(ApplicationInvariantError):
    """The festival signs a contract per application and no payer has been named."""


class NotAllSubmissionsApprovedError(ApplicationInvariantError):
    """The application is not ready for payment because not all its submissions are approved."""
