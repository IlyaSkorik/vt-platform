"""Domain exceptions for the Participants bounded context.

Typed, framework-free domain errors. They are raised by the domain (entities,
value objects, services, policies) and mapped to RFC 9457 Problem Details at the
presentation edge (ARCH-001 §7.6). No Django/DRF imports.

The hierarchy mirrors the Identity reference context (ARCH-001 §7.2) and is
intentionally shallow:

    ParticipantsDomainError                 — base for every Participants domain error
    ├── ValueObjectValidationError          — a value object rejected its input
    │   ├── InvalidParticipantIdError
    │   ├── InvalidGuardianIdError
    │   ├── InvalidTeacherIdError
    │   ├── InvalidInstitutionIdError
    │   ├── InvalidPersonNameError
    │   ├── InvalidDateOfBirthError
    │   ├── InvalidDisplayAliasError
    │   └── InvalidConsentReferenceError
    ├── PolicyConfigurationError            — a policy was injected invalid configuration
    ├── PolicyViolationError                — a business policy rejected an operation
    │   └── AgeGroupUndefinedError
    ├── DirectConstructionError             — the Participant aggregate bypassed its factories
    └── ParticipantStateError               — an operation illegal in the aggregate's current state
        ├── ParticipantErasedError
        ├── ParticipantNotArchivedError
        ├── InvalidParticipantTransitionError
        ├── GuardianAlreadyLinkedError
        ├── GuardianLinkNotFoundError
        ├── GuardianLinkNotPendingError
        ├── ActivationRequirementsError
        └── ConsentNotRecordedError
"""

from __future__ import annotations

__all__ = [
    "ActivationRequirementsError",
    "AgeGroupUndefinedError",
    "AliasRevealsIdentityError",
    "ConsentNotRecordedError",
    "DirectConstructionError",
    "GuardianAlreadyLinkedError",
    "GuardianLinkNotFoundError",
    "GuardianLinkNotPendingError",
    "InvalidConsentReferenceError",
    "InvalidDateOfBirthError",
    "InvalidDisplayAliasError",
    "InvalidGuardianIdError",
    "InvalidInstitutionIdError",
    "InvalidParticipantIdError",
    "InvalidParticipantTransitionError",
    "InvalidPersonNameError",
    "InvalidTeacherIdError",
    "ParticipantErasedError",
    "ParticipantNotArchivedError",
    "ParticipantStateError",
    "ParticipantsDomainError",
    "PolicyConfigurationError",
    "PolicyViolationError",
    "ValueObjectValidationError",
]


class ParticipantsDomainError(Exception):
    """Base class for all errors raised by the Participants domain."""


class ValueObjectValidationError(ParticipantsDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so that callers treating construction like any
    other value parsing continue to work, while still being catchable as a
    domain-specific error.
    """


class InvalidParticipantIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ParticipantId`` (must be a UUID v7)."""


class InvalidGuardianIdError(ValueObjectValidationError):
    """The provided value is not a valid ``GuardianId`` (must be a UUID v7)."""


class InvalidTeacherIdError(ValueObjectValidationError):
    """The provided value is not a valid ``TeacherId`` (must be a UUID v7)."""


class InvalidInstitutionIdError(ValueObjectValidationError):
    """The provided value is not a valid ``InstitutionId`` (must be a UUID v7)."""


class InvalidPersonNameError(ValueObjectValidationError):
    """The provided name parts are invalid (empty, too long, or disallowed characters)."""


class InvalidDateOfBirthError(ValueObjectValidationError):
    """The provided value is not a valid date of birth (future, or out of bounds)."""


class InvalidDisplayAliasError(ValueObjectValidationError):
    """The provided value is not a valid pseudonymized display alias (DATA-001 §4.2)."""


class InvalidConsentReferenceError(ValueObjectValidationError):
    """The provided value is not a valid consent reference (bad id or version)."""


class PolicyConfigurationError(ParticipantsDomainError, ValueError):
    """Raised when a business policy is constructed with invalid configuration.

    Policies are configured by injection (never from globals or files), so a
    nonsensical knob — overlapping age bands, a maximum below a minimum — is a
    caller/composition bug, not a domain-runtime condition. Subclasses
    :class:`ValueError` so it reads naturally at the composition root while still
    being catchable as a Participants domain error.
    """


class PolicyViolationError(ParticipantsDomainError):
    """Base class for a business policy rejecting an operation at runtime.

    Distinct from :class:`ValueObjectValidationError` (a value that cannot exist)
    and :class:`PolicyConfigurationError` (a misconfigured policy): the inputs are
    individually valid, but a *business rule* forbids the operation. Mapped to RFC
    9457 Problem Details at the presentation edge (ARCH-001 §7.6).
    """


class AgeGroupUndefinedError(PolicyViolationError):
    """No configured age band covers the participant's derived age (PRT-002).

    Age group is always derived from date of birth relative to a competition's
    reference date; when the configured bands leave the derived age uncovered the
    platform must surface it rather than fabricate a cohort.
    """


class AliasRevealsIdentityError(PolicyViolationError):
    """A display alias would leak the participant's real name to judging (JDG-006, PRT-006).

    Judges must see only the pseudonymized alias; an alias that embeds a
    significant part of the real :class:`~apps.participants.domain.value_objects.PersonName`
    defeats blind judging and is refused.
    """


class DirectConstructionError(ParticipantsDomainError):
    """Raised when :class:`~apps.participants.domain.entities.Participant` is built directly.

    The aggregate root must be created through ``Participant.create`` (a new
    participant) or ``Participant.rehydrate`` (reconstruction from persistence),
    which alone establish the creation invariants. Calling the dataclass
    constructor directly bypasses them and is therefore refused.
    """


class ParticipantStateError(ParticipantsDomainError):
    """Base for an operation illegal in the Participant aggregate's current state.

    The inputs are individually valid, but the aggregate's lifecycle
    (DATA-004 §4.3: Created → Verified → Active → Archived → Erased) forbids the
    transition. Mapped to RFC 9457 Problem Details at the presentation edge
    (ARCH-001 §7.6).
    """


class ParticipantErasedError(ParticipantStateError):
    """The operation is not permitted because the participant has been erased.

    ``Erased`` is the terminal, irreversible state of the lifecycle
    (DATA-004 §4.3, TRN-PRT-004); no further transition or mutation is allowed.
    """


class ParticipantNotArchivedError(ParticipantStateError):
    """A reactivation was attempted on a participant that is not archived."""


class InvalidParticipantTransitionError(ParticipantStateError):
    """A lifecycle transition was requested from a state that does not allow it.

    Raised when, e.g., activating a participant that is not ``Verified`` or
    archiving one that is not ``Active`` (DATA-004 §4.3).
    """


class GuardianAlreadyLinkedError(ParticipantStateError):
    """A guardian link was proposed for a guardian already linked to the participant.

    Duplicate guardian relationships require review before both become active
    (PRT-008); the aggregate refuses a straightforward duplicate outright.
    """


class GuardianLinkNotFoundError(ParticipantStateError):
    """The referenced guardian is not linked to this participant."""


class GuardianLinkNotPendingError(ParticipantStateError):
    """The guardian link is not in the ``Proposed`` state and cannot be verified."""


class ActivationRequirementsError(ParticipantStateError):
    """Activation was blocked because its preconditions are not met (PRT-001).

    A participant may not become ``Active`` without at least one active guardian
    relationship *or* an authorized institution/teacher link, **and** an active,
    recorded consent (PRT-001, DATA-004 TRN-PRT-002). :attr:`reason` carries the
    machine-readable cause for precise presentation mapping.
    """

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class ConsentNotRecordedError(ParticipantStateError):
    """A consent withdrawal was attempted, but no active consent is recorded."""
