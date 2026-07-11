"""Domain exceptions for the Competitions bounded context.

Typed, framework-free domain errors raised by the domain (entities, value
objects, policies) and mapped to RFC 9457 Problem Details at the presentation
edge (ARCH-001 §7.6). No Django/DRF imports.

    CompetitionDomainError                      — base for every error in this context
    ├── ValueObjectValidationError              — a value object rejected its input
    │   ├── InvalidCompetitionIdError
    │   ├── InvalidCategoryIdError
    │   ├── InvalidDisciplineIdError
    │   ├── InvalidAgeCategoryIdError
    │   ├── InvalidParticipantGroupIdError
    │   ├── InvalidRegulationIdError
    │   ├── InvalidDocumentIdError
    │   ├── InvalidOrganizerIdError
    │   ├── InvalidCompetitionTitleError
    │   ├── InvalidCompetitionDescriptionError
    │   ├── InvalidSeasonError
    │   ├── InvalidVenueError
    │   ├── InvalidFileReferenceError
    │   ├── InvalidDateRangeError
    │   ├── InvalidAgeRangeError
    │   ├── InvalidParticipantCountRangeError
    │   ├── InvalidCategoryNameError
    │   ├── InvalidCategoryDescriptionError
    │   ├── InvalidDisciplineNameError
    │   ├── InvalidParticipantGroupNameError
    │   ├── InvalidParticipantGroupDescriptionError
    │   ├── InvalidRegulationTitleError
    │   ├── InvalidRegulationVersionError
    │   ├── InvalidDocumentTitleError
    │   ├── InvalidDocumentDescriptionError
    │   ├── InvalidSortOrderError
    │   ├── InvalidMoneyError
    │   ├── InvalidTemplateIdError
    │   ├── InvalidTemplateNameError
    │   ├── InvalidServiceIdError
    │   ├── InvalidServiceNameError
    │   └── InvalidServiceDescriptionError
    ├── DirectConstructionError                 — an aggregate was built bypassing its factories
    ├── CompetitionStateError                   — an operation illegal in the Competition's lifecycle
    │   ├── ConfigurationLockedError            — configuration edited when not editable (post-CONFIGURED)
    │   ├── CompetitionAlreadyPublishedError
    │   ├── CompetitionAlreadyArchivedError
    │   ├── IllegalStatusTransitionError        — the requested lifecycle transition is not legal
    │   └── PublicationRequirementsNotMetError  — publish attempted on an incomplete configuration
    ├── ConfigurationReferenceError             — a rule/child references a config element that is absent
    │   ├── CategoryNotFoundError
    │   ├── DisciplineNotFoundError
    │   ├── AgeCategoryNotFoundError
    │   ├── ParticipantGroupNotFoundError
    │   ├── RegulationNotFoundError
    │   ├── DocumentNotFoundError
    │   ├── ServiceNotFoundError
    │   ├── ParticipationFormatNotEnabledError
    │   ├── AdmissionRuleNotFoundError
    │   ├── PricingRuleNotFoundError
    │   ├── DisciplineCategoryMismatchError     — discipline belongs to a different category
    │   └── ParticipantGroupCategoryMismatchError
    ├── ConfigurationConflictError              — a config element would duplicate/overlap an existing one
    │   ├── DuplicateCategoryError
    │   ├── DuplicateDisciplineError
    │   ├── DuplicateAgeCategoryError
    │   ├── OverlappingAgeRangeError
    │   ├── DuplicateParticipantGroupError
    │   ├── OverlappingParticipantRangeError
    │   ├── DuplicateAdmissionRuleError
    │   └── DuplicatePricingRuleError
    └── ConfigurationInUseError                 — a config element cannot be removed while referenced
        ├── CategoryInUseError
        ├── DisciplineInUseError
        ├── AgeCategoryInUseError
        ├── ParticipantGroupInUseError
        ├── ParticipationFormatInUseError
        └── AdmissionRuleInUseError
"""

from __future__ import annotations


class CompetitionDomainError(Exception):
    """Base class for all errors raised by the Competitions domain."""


# ---------------------------------------------------------------------------
# Value-object validation
# ---------------------------------------------------------------------------


class ValueObjectValidationError(CompetitionDomainError, ValueError):
    """Raised when a value object is constructed from invalid input.

    Subclasses :class:`ValueError` so callers treating construction like value
    parsing keep working, while still being catchable as a domain-specific error.
    """


class InvalidCompetitionIdError(ValueObjectValidationError):
    """The provided value is not a valid ``CompetitionId`` (must be a UUID v7)."""


class InvalidCategoryIdError(ValueObjectValidationError):
    """The provided value is not a valid ``CategoryId`` (must be a UUID v7)."""


class InvalidDisciplineIdError(ValueObjectValidationError):
    """The provided value is not a valid ``DisciplineId`` (must be a UUID v7)."""


class InvalidAgeCategoryIdError(ValueObjectValidationError):
    """The provided value is not a valid ``AgeCategoryId`` (must be a UUID v7)."""


class InvalidParticipantGroupIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ParticipantGroupId`` (must be a UUID v7)."""


class InvalidRegulationIdError(ValueObjectValidationError):
    """The provided value is not a valid ``RegulationId`` (must be a UUID v7)."""


class InvalidDocumentIdError(ValueObjectValidationError):
    """The provided value is not a valid ``DocumentId`` (must be a UUID v7)."""


class InvalidOrganizerIdError(ValueObjectValidationError):
    """The provided value is not a valid ``OrganizerId`` (must be a UUID v7)."""


class InvalidCompetitionTitleError(ValueObjectValidationError):
    """The provided value is not a valid competition title (empty or too long)."""


class InvalidCompetitionDescriptionError(ValueObjectValidationError):
    """The provided value is not a valid competition description (too long)."""


class InvalidSeasonError(ValueObjectValidationError):
    """The provided value is not a valid season label (empty or too long)."""


class InvalidVenueError(ValueObjectValidationError):
    """The provided value is not a valid venue (empty name or over-long fields)."""


class InvalidFileReferenceError(ValueObjectValidationError):
    """The provided value is not a valid file reference (empty or too long)."""


class InvalidDateRangeError(ValueObjectValidationError):
    """The provided dates do not form a valid range (end precedes start)."""


class InvalidAgeRangeError(ValueObjectValidationError):
    """The provided ages do not form a valid range (out of bounds or inverted)."""


class InvalidParticipantCountRangeError(ValueObjectValidationError):
    """The provided counts do not form a valid participant-count range."""


class InvalidCategoryNameError(ValueObjectValidationError):
    """The provided value is not a valid category name (empty or too long)."""


class InvalidDisciplineNameError(ValueObjectValidationError):
    """The provided value is not a valid discipline name (empty or too long)."""


class InvalidParticipantGroupNameError(ValueObjectValidationError):
    """The provided value is not a valid participant-group name (empty or too long)."""


class InvalidRegulationTitleError(ValueObjectValidationError):
    """The provided value is not a valid regulation title (empty or too long)."""


class InvalidRegulationVersionError(ValueObjectValidationError):
    """The provided value is not a valid regulation version label (empty or too long)."""


class InvalidDocumentTitleError(ValueObjectValidationError):
    """The provided value is not a valid document title (empty or too long)."""


class InvalidDocumentDescriptionError(ValueObjectValidationError):
    """The provided value is not a valid document description (too long)."""


class InvalidSortOrderError(ValueObjectValidationError):
    """The provided value is not a valid sort order (must be a non-negative integer)."""


class InvalidMoneyError(ValueObjectValidationError):
    """The provided value is not a valid monetary amount (negative or malformed)."""


class InvalidTemplateIdError(ValueObjectValidationError):
    """The provided value is not a valid ``TemplateId`` (must be a UUID v7)."""


class InvalidTemplateNameError(ValueObjectValidationError):
    """The provided value is not a valid template name (empty or too long)."""


class InvalidServiceIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ServiceId`` (must be a UUID v7)."""


class InvalidServiceNameError(ValueObjectValidationError):
    """The provided value is not a valid additional-service name (empty or too long)."""


class InvalidCategoryDescriptionError(ValueObjectValidationError):
    """The provided value is not a valid category description (too long)."""


class InvalidParticipantGroupDescriptionError(ValueObjectValidationError):
    """The provided value is not a valid participant-group description (too long)."""


class InvalidServiceDescriptionError(ValueObjectValidationError):
    """The provided value is not a valid additional-service description (too long)."""


class InvalidRichTextError(ValueObjectValidationError):
    """The provided value is not valid rich-text content (too long)."""


class InvalidContactIdError(ValueObjectValidationError):
    """The provided value is not a valid ``ContactId`` (must be a UUID v7)."""


class InvalidInformationBlockIdError(ValueObjectValidationError):
    """The provided value is not a valid ``InformationBlockId`` (must be a UUID v7)."""


class InvalidContactValueError(ValueObjectValidationError):
    """The provided value is not a valid contact value (empty or too long)."""


class InvalidInformationBlockTitleError(ValueObjectValidationError):
    """The provided value is not a valid information-block title (empty or too long)."""


class InvalidAgeCategoryNameError(ValueObjectValidationError):
    """The provided value is not a valid age-category name (empty or too long)."""


class InvalidRegistrationDeadlinesError(ValueObjectValidationError):
    """The provided registration deadlines contradict one another."""


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class DirectConstructionError(CompetitionDomainError):
    """Raised when an aggregate is built directly instead of via its factories.

    The :class:`~apps.competitions.domain.entities.Competition` aggregate root
    must be created through its ``draft`` factory (a new instance) or
    ``rehydrate`` (reconstruction from persistence), which alone establish the
    creation invariants. Calling the dataclass constructor directly bypasses them
    and is refused.
    """


# ---------------------------------------------------------------------------
# Lifecycle state
# ---------------------------------------------------------------------------


class CompetitionStateError(CompetitionDomainError):
    """Base for an operation illegal in the ``Competition`` aggregate's lifecycle state."""


class ConfigurationLockedError(CompetitionStateError):
    """Configuration was edited while the competition is not in DRAFT.

    A competition's constructor (categories, disciplines, rules, pricing, …) is
    mutable only while ``DRAFT``. Once ``PUBLISHED`` the configuration is frozen so
    that applications already resting on it cannot be invalidated underneath them.
    """


class CompetitionAlreadyPublishedError(CompetitionStateError):
    """The competition is already published; it cannot be published again."""


class CompetitionAlreadyArchivedError(CompetitionStateError):
    """The competition is already archived; the operation is not permitted."""


class IllegalStatusTransitionError(CompetitionStateError):
    """The requested lifecycle transition is not legal from the current status."""


class PublicationRequirementsNotMetError(CompetitionStateError):
    """Publication was attempted while the configuration is incomplete.

    A competition can only open to applicants once its constructor is coherent:
    at least one category, discipline, age category, participant group and enabled
    participation format, at least one admission rule, and a price for every
    admissible combination.
    """


# ---------------------------------------------------------------------------
# Referential integrity within the aggregate
# ---------------------------------------------------------------------------


class ConfigurationReferenceError(CompetitionDomainError):
    """Base: a rule or child references a configuration element that does not exist."""


class CategoryNotFoundError(ConfigurationReferenceError):
    """The referenced category does not exist in this competition."""


class DisciplineNotFoundError(ConfigurationReferenceError):
    """The referenced discipline does not exist in this competition."""


class AgeCategoryNotFoundError(ConfigurationReferenceError):
    """The referenced age category does not exist in this competition."""


class ParticipantGroupNotFoundError(ConfigurationReferenceError):
    """The referenced participant group does not exist in this competition."""


class RegulationNotFoundError(ConfigurationReferenceError):
    """The referenced regulation does not exist in this competition."""


class DocumentNotFoundError(ConfigurationReferenceError):
    """The referenced document does not exist in this competition."""


class ServiceNotFoundError(ConfigurationReferenceError):
    """The referenced additional service does not exist in this competition."""


class ContactNotFoundError(ConfigurationReferenceError):
    """The referenced contact does not exist in this competition."""


class InformationBlockNotFoundError(ConfigurationReferenceError):
    """The referenced public-information block does not exist in this competition."""


class ParticipationFormatNotEnabledError(ConfigurationReferenceError):
    """The referenced participation format is not enabled for this competition."""


class AdmissionRuleNotFoundError(ConfigurationReferenceError):
    """No admission rule exists for the referenced combination."""


class PricingRuleNotFoundError(ConfigurationReferenceError):
    """No pricing rule exists for the referenced combination."""


class DisciplineCategoryMismatchError(ConfigurationReferenceError):
    """The referenced discipline belongs to a different category than stated."""


class AgeCategoryCategoryMismatchError(ConfigurationReferenceError):
    """The referenced age category belongs to a different category than stated."""


class ParticipantGroupCategoryMismatchError(ConfigurationReferenceError):
    """The referenced participant group belongs to a different category than stated."""


# ---------------------------------------------------------------------------
# Uniqueness conflicts
# ---------------------------------------------------------------------------


class ConfigurationConflictError(CompetitionDomainError):
    """Base: a configuration element would duplicate one that already exists."""


class DuplicateCategoryError(ConfigurationConflictError):
    """A category with the same name already exists in this competition."""


class DuplicateDisciplineError(ConfigurationConflictError):
    """A discipline with the same name already exists in its category."""


class DuplicateAgeCategoryError(ConfigurationConflictError):
    """An age category with the same range already exists in this competition."""


class DuplicateAgeCategoryNameError(ConfigurationConflictError):
    """An age category with the same name already exists in this nomination (category)."""


class OverlappingAgeRangeError(ConfigurationConflictError):
    """An age category whose range overlaps an existing one is not allowed."""


class OverlappingParticipantRangeError(ConfigurationConflictError):
    """A participant group whose count range overlaps another in the same category."""


class DuplicateParticipantGroupError(ConfigurationConflictError):
    """A participant group with the same name already exists in its category."""


class DuplicateAdmissionRuleError(ConfigurationConflictError):
    """An admission rule for the same combination already exists."""


class DuplicatePricingRuleError(ConfigurationConflictError):
    """A pricing rule for the same combination already exists."""


class DuplicateContactError(ConfigurationConflictError):
    """A contact with the same type and value already exists."""


class DuplicateInformationBlockError(ConfigurationConflictError):
    """An information block with the same title already exists."""


# ---------------------------------------------------------------------------
# Deletion guards
# ---------------------------------------------------------------------------


class ConfigurationInUseError(CompetitionDomainError):
    """Base: a configuration element cannot be removed while it is still referenced."""


class CategoryInUseError(ConfigurationInUseError):
    """The category is referenced by disciplines, groups, or rules and cannot be removed."""


class DisciplineInUseError(ConfigurationInUseError):
    """The discipline is referenced by admission or pricing rules and cannot be removed."""


class AgeCategoryInUseError(ConfigurationInUseError):
    """The age category is referenced by admission or pricing rules and cannot be removed."""


class ParticipantGroupInUseError(ConfigurationInUseError):
    """The participant group is referenced by admission or pricing rules and cannot be removed."""


class ParticipationFormatInUseError(ConfigurationInUseError):
    """The participation format is referenced by admission or pricing rules and cannot be disabled."""


class AdmissionRuleInUseError(ConfigurationInUseError):
    """The admission rule underpins a pricing rule and cannot be removed while priced."""
