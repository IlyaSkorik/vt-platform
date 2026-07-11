"""Domain entities for the Competitions bounded context.

One aggregate — the :class:`Competition` — modelled as a **configurable
constructor**: an organizer assembles a competition's taxonomy (categories,
disciplines, age bands, participant groups), the participation formats it
supports, the combinations it *admits*, and the *price per participant* for each,
entirely as data. Nothing here is hardcoded.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no Django, no
ORM, no clock, no IO. Time is always supplied by the caller (``now``).

Design contract (mirrors the Identity ``User`` and Organization aggregates):

* **No direct construction of the root.** Build a :class:`Competition` only via
  :meth:`Competition.draft` or :meth:`Competition.rehydrate` (reconstruction from
  persistence, which re-validates nothing and emits nothing).
* **Encapsulated state.** All fields private; only read-only views exposed. Child
  entities and configuration are mutated **only** through root methods, so every
  cross-element invariant is enforced in one place.
* **Root behaviour returns events, never publishes them.** Lifecycle methods
  validate invariants, mutate state, bump ``updated_at``/``version``, and return
  the domain events they produced. Dispatch is an outer-layer concern.
* **Invalid transitions raise** typed errors — never silently ignored.

**Aggregate boundary.** Categories, disciplines, age categories, participant
groups, regulations, documents, additional services, contacts and public
information blocks are **child entities** of the Competition (local identity, no
independent version — the root carries the aggregate's optimistic-concurrency
version). Admission and pricing rules are **value objects** (configuration facts
keyed by their combination); so are the cohesive behaviour/branding/deadline
bundles — :class:`~apps.competitions.domain.value_objects.CompetitionSettings`,
:class:`~apps.competitions.domain.value_objects.CompetitionBranding` and
:class:`~apps.competitions.domain.value_objects.RegistrationDeadlines` — which keep
their many fields off the root rather than scattering flags across it. Everything
loads and saves as one unit because the admission/pricing invariants are
*referential*: a rule may only name elements that exist in the same competition,
so they must live inside a single consistency boundary. A separate
:class:`~apps.competitions.domain.templates.CompetitionTemplate` aggregate holds a
reusable copy of the taxonomy/format/rule graph; :meth:`Competition.from_template`
clones it into a fresh draft.

**Future extension points (documented, deliberately NOT implemented).** The model
is shaped so these land as *additions*, not rewrites:

* *Multilingual competitions* — general-information VOs and
  :class:`~apps.competitions.domain.value_objects.RichText` become locale-keyed
  (e.g. ``Mapping[Locale, RichText]``); the aggregate shape is unchanged.
* *Regional competitions* — a ``Region`` value object referenced by id, plus
  region-scoped pricing (see ``Money``'s regional-pricing note).
* *Online streaming* — a new ``ParticipationFormat`` member and/or a streaming
  child entity holding stream references.
* *Promo codes / discounts / coupons* — a checkout-stage concern (Application/
  Payments), computed *from* the list price in ``PricingRule``, never stored on it.
* *Sponsorship* — a ``Sponsor`` child entity (name, tier, logo ``FileReference``).
* *Accommodation / transport booking* — new bounded contexts referencing the
  competition by id; here only the informational blocks and documents exist.
* *Certificates* — a Results/Diploma context concern, out of scope.
* *Custom application fields* — a form-schema value object the Application context
  reads; the Competition would own the schema, not the submitted values.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Final

from .events import (
    AdditionalServiceAdded,
    AdmissionRuleAdded,
    AdmissionRuleRemoved,
    CompetitionArchived,
    CompetitionBrandingChanged,
    CompetitionCompleted,
    CompetitionContactAdded,
    CompetitionContactRemoved,
    CompetitionCreated,
    CompetitionDeadlineChanged,
    CompetitionGeneralInformationUpdated,
    CompetitionInformationHidden,
    CompetitionInformationPublished,
    CompetitionPublished,
    CompetitionRegistrationClosed,
    CompetitionRegistrationOpened,
    CompetitionSettingsChanged,
    CompetitionStarted,
    DomainEvent,
    ParticipationFormatDisabled,
    ParticipationFormatEnabled,
    PricingRuleAdded,
    PricingRuleRemoved,
    RegulationPublished,
)
from .exceptions import (
    AdmissionRuleInUseError,
    AdmissionRuleNotFoundError,
    AgeCategoryCategoryMismatchError,
    AgeCategoryInUseError,
    AgeCategoryNotFoundError,
    CategoryInUseError,
    CategoryNotFoundError,
    DuplicateAgeCategoryNameError,
    CompetitionAlreadyArchivedError,
    ConfigurationLockedError,
    ContactNotFoundError,
    DirectConstructionError,
    DisciplineCategoryMismatchError,
    DisciplineInUseError,
    DisciplineNotFoundError,
    DocumentNotFoundError,
    DuplicateAdmissionRuleError,
    DuplicateCategoryError,
    DuplicateContactError,
    DuplicateDisciplineError,
    DuplicateInformationBlockError,
    DuplicateParticipantGroupError,
    DuplicatePricingRuleError,
    IllegalStatusTransitionError,
    InformationBlockNotFoundError,
    InvalidSortOrderError,
    OverlappingAgeRangeError,
    OverlappingParticipantRangeError,
    ParticipantGroupCategoryMismatchError,
    ParticipantGroupInUseError,
    ParticipantGroupNotFoundError,
    ParticipationFormatInUseError,
    ParticipationFormatNotEnabledError,
    PricingRuleNotFoundError,
    PublicationRequirementsNotMetError,
    RegulationNotFoundError,
    ServiceNotFoundError,
)
from .value_objects import (
    AdmissionCombination,
    AdmissionRule,
    AgeCategoryId,
    AgeCategoryName,
    AgeCategoryType,
    AgeRange,
    CategoryDescription,
    CategoryId,
    CategoryName,
    CompetitionBranding,
    CompetitionDescription,
    CompetitionId,
    CompetitionPublicationReport,
    CompetitionSettings,
    CompetitionStatus,
    CompetitionTitle,
    ContactId,
    ContactType,
    ContactValue,
    DateRange,
    DeadlineKind,
    DisciplineId,
    DisciplineName,
    DocumentCategory,
    DocumentDescription,
    DocumentId,
    DocumentTitle,
    DocumentVisibility,
    FileReference,
    InformationBlockId,
    InformationBlockTitle,
    MixedAgeCalculationMethod,
    Money,
    OrganizerId,
    ParticipantCountRange,
    ParticipantGroupDescription,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormat,
    PricingRule,
    PublicationIssue,
    PublicationIssueCode,
    RegistrationDeadlines,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    Season,
    ServiceDescription,
    ServiceId,
    ServiceName,
    Venue,
)

if TYPE_CHECKING:
    from .templates import CompetitionTemplate

__all__ = [
    "AdditionalService",
    "AgeCategory",
    "Category",
    "Competition",
    "CompetitionDocument",
    "CompetitionRegulation",
    "Contact",
    "Discipline",
    "InformationBlock",
    "ParticipantGroup",
]

#: Opaque capability token proving the root's construction went through a factory.
_CREATION_TOKEN: Final = object()

#: Sentinel for distinguishing "not supplied" from ``None`` in partial updates.
_SENTINEL: Final = object()

#: The lifecycle transitions the aggregate permits. ``ARCHIVED`` is terminal, and
#: any non-archived status may transition to ``ARCHIVED`` (see :meth:`Competition.archive`).
_LEGAL_TRANSITIONS: Final[dict[CompetitionStatus, frozenset[CompetitionStatus]]] = {
    CompetitionStatus.DRAFT: frozenset({CompetitionStatus.CONFIGURED, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.CONFIGURED: frozenset({CompetitionStatus.DRAFT, CompetitionStatus.READY, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.READY: frozenset({CompetitionStatus.CONFIGURED, CompetitionStatus.PUBLISHED, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.PUBLISHED: frozenset({CompetitionStatus.REGISTRATION_OPEN, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.REGISTRATION_OPEN: frozenset({CompetitionStatus.REGISTRATION_CLOSED, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.REGISTRATION_CLOSED: frozenset({CompetitionStatus.RUNNING, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.RUNNING: frozenset({CompetitionStatus.COMPLETED, CompetitionStatus.ARCHIVED}),
    CompetitionStatus.COMPLETED: frozenset({CompetitionStatus.ARCHIVED}),
    CompetitionStatus.ARCHIVED: frozenset(),
}

#: Statuses in which the admissibility configuration (taxonomy, formats, admission
#: and pricing rules) may still be mutated. Beyond these it is frozen.
_CONFIGURABLE_STATUSES: Final = frozenset({CompetitionStatus.DRAFT, CompetitionStatus.CONFIGURED})


# ===========================================================================
# Shared configuration-validation helpers
# ===========================================================================
#
# Pure, stateless invariant checks over a configuration graph, shared by the
# :class:`Competition` aggregate and the :class:`~apps.competitions.domain.
# templates.CompetitionTemplate` aggregate so both enforce identical rules without
# duplicating logic. They raise the same typed domain errors either aggregate does.


def ensure_admission_combination_valid(
    combination: AdmissionCombination,
    *,
    categories: Mapping[CategoryId, Category],
    disciplines: Mapping[DisciplineId, Discipline],
    age_categories: Mapping[AgeCategoryId, AgeCategory],
    participant_groups: Mapping[ParticipantGroupId, ParticipantGroup],
    formats: frozenset[ParticipationFormat] | set[ParticipationFormat],
) -> None:
    """Assert every element ``combination`` references exists and is mutually consistent."""
    if combination.category_id not in categories:
        raise CategoryNotFoundError(f"No category {combination.category_id} in this configuration.")
    discipline = disciplines.get(combination.discipline_id)
    if discipline is None:
        raise DisciplineNotFoundError(f"No discipline {combination.discipline_id} in this configuration.")
    if discipline.category_id != combination.category_id:
        raise DisciplineCategoryMismatchError("The discipline does not belong to the stated category.")
    age_category = age_categories.get(combination.age_category_id)
    if age_category is None:
        raise AgeCategoryNotFoundError(f"No age category {combination.age_category_id} in this configuration.")
    if age_category.category_id != combination.category_id:
        raise AgeCategoryCategoryMismatchError("The age category does not belong to the stated category.")
    group = participant_groups.get(combination.participant_group_id)
    if group is None:
        raise ParticipantGroupNotFoundError(f"No participant group {combination.participant_group_id} in this configuration.")
    if group.category_id != combination.category_id:
        raise ParticipantGroupCategoryMismatchError("The participant group does not belong to the stated category.")
    if combination.participation_format not in formats:
        raise ParticipationFormatNotEnabledError(f"Participation format {combination.participation_format.value} is not enabled.")


def ensure_age_range_free(
    age_categories: Mapping[AgeCategoryId, AgeCategory],
    age_range: AgeRange,
    *,
    category_id: CategoryId,
    exclude: AgeCategoryId | None = None,
) -> None:
    """Assert ``age_range`` does not overlap any existing age category within the same nomination."""
    for aid, existing in age_categories.items():
        if aid == exclude:
            continue
        if existing.category_id != category_id:
            continue
        if existing.age_range.overlaps(age_range):
            raise OverlappingAgeRangeError(f"Age range {age_range} overlaps existing range {existing.age_range}.")


def ensure_participant_range_free(
    participant_groups: Mapping[ParticipantGroupId, ParticipantGroup],
    category_id: CategoryId,
    count_range: ParticipantCountRange,
    *,
    exclude: ParticipantGroupId | None = None,
) -> None:
    """Assert ``count_range`` does not overlap another group's range in the same category."""
    for gid, existing in participant_groups.items():
        if gid == exclude or existing.category_id != category_id:
            continue
        if existing.count_range.overlaps(count_range):
            raise OverlappingParticipantRangeError(
                f"Participant range {count_range} overlaps existing range {existing.count_range} in this category."
            )


# ===========================================================================
# Child entities
# ===========================================================================
#
# Child entities have local identity and value-by-id equality but carry **no**
# optimistic-concurrency version and emit no events — the root owns the
# aggregate's version and its event stream. They are created and mutated only by
# the :class:`Competition` root (their ``create``/``rehydrate`` classmethods are
# aggregate-internal by convention), which is why they need no direct-construction
# token of their own.


@dataclass(slots=True, eq=False, repr=False)
class Category:
    """A competition category — the top of the taxonomy (e.g. Vocal, Choreography)."""

    _id: CategoryId
    _name: CategoryName
    _description: CategoryDescription | None = None
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        category_id: CategoryId,
        name: CategoryName,
        description: CategoryDescription | None = None,
        sort_order: int = 0,
    ) -> Category:
        return cls(_id=category_id, _name=name, _description=description, _sort_order=_validate_sort_order(sort_order))

    @classmethod
    def rehydrate(
        cls,
        *,
        category_id: CategoryId,
        name: CategoryName,
        description: CategoryDescription | None = None,
        sort_order: int = 0,
    ) -> Category:
        return cls(_id=category_id, _name=name, _description=description, _sort_order=sort_order)

    @property
    def id(self) -> CategoryId:
        return self._id

    @property
    def name(self) -> CategoryName:
        return self._name

    @property
    def description(self) -> CategoryDescription | None:
        return self._description

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def rename(self, name: CategoryName) -> None:
        self._name = name

    def update(
        self,
        *,
        name: CategoryName | None = None,
        description: CategoryDescription | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        if name is not None:
            self._name = name
        if description is not _SENTINEL:
            self._description = description
        if sort_order is not None:
            self._sort_order = _validate_sort_order(sort_order)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Category) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Category(id={self._id!r}, name={self._name.value!r})"


@dataclass(slots=True, eq=False, repr=False)
class Discipline:
    """A discipline within a category (e.g. Pop / Folk / Academic under Vocal)."""

    _id: DisciplineId
    _category_id: CategoryId
    _name: DisciplineName
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        discipline_id: DisciplineId,
        category_id: CategoryId,
        name: DisciplineName,
        sort_order: int = 0,
    ) -> Discipline:
        return cls(_id=discipline_id, _category_id=category_id, _name=name, _sort_order=_validate_sort_order(sort_order))

    @classmethod
    def rehydrate(
        cls,
        *,
        discipline_id: DisciplineId,
        category_id: CategoryId,
        name: DisciplineName,
        sort_order: int = 0,
    ) -> Discipline:
        return cls(_id=discipline_id, _category_id=category_id, _name=name, _sort_order=sort_order)

    @property
    def id(self) -> DisciplineId:
        return self._id

    @property
    def category_id(self) -> CategoryId:
        return self._category_id

    @property
    def name(self) -> DisciplineName:
        return self._name

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def rename(self, name: DisciplineName) -> None:
        self._name = name

    def update(self, *, name: DisciplineName | None = None, sort_order: int | None = None) -> None:
        if name is not None:
            self._name = name
        if sort_order is not None:
            self._sort_order = _validate_sort_order(sort_order)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Discipline) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Discipline(id={self._id!r}, category_id={self._category_id!r}, name={self._name.value!r})"


@dataclass(slots=True, eq=False, repr=False)
class AgeCategory:
    """An age band configured for this competition, scoped to a nomination (category)."""

    _id: AgeCategoryId
    _category_id: CategoryId
    _name: AgeCategoryName
    _age_range: AgeRange
    _type: AgeCategoryType = AgeCategoryType.STANDARD
    _mixed_calculation_method: MixedAgeCalculationMethod | None = None
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        age_category_id: AgeCategoryId,
        category_id: CategoryId,
        name: AgeCategoryName,
        age_range: AgeRange,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int = 0,
    ) -> AgeCategory:
        _validate_type_method_consistency(age_category_type, mixed_calculation_method)
        return cls(
            _id=age_category_id,
            _category_id=category_id,
            _name=name,
            _age_range=age_range,
            _type=age_category_type,
            _mixed_calculation_method=mixed_calculation_method,
            _sort_order=_validate_sort_order(sort_order),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        age_category_id: AgeCategoryId,
        category_id: CategoryId,
        name: AgeCategoryName,
        age_range: AgeRange,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int = 0,
    ) -> AgeCategory:
        return cls(
            _id=age_category_id,
            _category_id=category_id,
            _name=name,
            _age_range=age_range,
            _type=age_category_type,
            _mixed_calculation_method=mixed_calculation_method,
            _sort_order=sort_order,
        )

    @property
    def id(self) -> AgeCategoryId:
        return self._id

    @property
    def category_id(self) -> CategoryId:
        return self._category_id

    @property
    def name(self) -> AgeCategoryName:
        return self._name

    @property
    def age_range(self) -> AgeRange:
        return self._age_range

    @property
    def type(self) -> AgeCategoryType:
        return self._type

    @property
    def mixed_calculation_method(self) -> MixedAgeCalculationMethod | None:
        return self._mixed_calculation_method

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def redefine(self, age_range: AgeRange) -> None:
        self._age_range = age_range

    def update(
        self,
        *,
        name: AgeCategoryName | None = None,
        age_range: AgeRange | None = None,
        age_category_type: AgeCategoryType | None = None,
        mixed_calculation_method: MixedAgeCalculationMethod | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        if name is not None:
            self._name = name
        if age_range is not None:
            self._age_range = age_range
        if age_category_type is not None:
            self._type = age_category_type
        if mixed_calculation_method is not _SENTINEL:
            self._mixed_calculation_method = mixed_calculation_method
        _validate_type_method_consistency(self._type, self._mixed_calculation_method)
        if sort_order is not None:
            self._sort_order = _validate_sort_order(sort_order)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AgeCategory) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"AgeCategory(id={self._id!r}, category_id={self._category_id!r}, name={self._name.value!r}, range={self._age_range})"


@dataclass(slots=True, eq=False, repr=False)
class ParticipantGroup:
    """A participant grouping mapped from a headcount band, scoped to a category.

    The mapping is configured per category (Vocal: Solo=1, Duet=2, Ensemble=3-5,
    Choir=6+; Instrumental: Orchestra=9+; …) — never a hardcoded string.
    """

    _id: ParticipantGroupId
    _category_id: CategoryId
    _name: ParticipantGroupName
    _count_range: ParticipantCountRange
    _description: ParticipantGroupDescription | None = None
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        participant_group_id: ParticipantGroupId,
        category_id: CategoryId,
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        description: ParticipantGroupDescription | None = None,
        sort_order: int = 0,
    ) -> ParticipantGroup:
        return cls(
            _id=participant_group_id,
            _category_id=category_id,
            _name=name,
            _count_range=count_range,
            _description=description,
            _sort_order=_validate_sort_order(sort_order),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        participant_group_id: ParticipantGroupId,
        category_id: CategoryId,
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        description: ParticipantGroupDescription | None = None,
        sort_order: int = 0,
    ) -> ParticipantGroup:
        return cls(
            _id=participant_group_id,
            _category_id=category_id,
            _name=name,
            _count_range=count_range,
            _description=description,
            _sort_order=sort_order,
        )

    @property
    def id(self) -> ParticipantGroupId:
        return self._id

    @property
    def category_id(self) -> CategoryId:
        return self._category_id

    @property
    def name(self) -> ParticipantGroupName:
        return self._name

    @property
    def count_range(self) -> ParticipantCountRange:
        return self._count_range

    @property
    def description(self) -> ParticipantGroupDescription | None:
        return self._description

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def rename(self, name: ParticipantGroupName) -> None:
        self._name = name

    def resize(self, count_range: ParticipantCountRange) -> None:
        self._count_range = count_range

    def update(
        self,
        *,
        name: ParticipantGroupName | None = None,
        count_range: ParticipantCountRange | None = None,
        description: ParticipantGroupDescription | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        if name is not None:
            self._name = name
        if count_range is not None:
            self._count_range = count_range
        if description is not _SENTINEL:
            self._description = description
        if sort_order is not None:
            self._sort_order = _validate_sort_order(sort_order)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ParticipantGroup) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ParticipantGroup(id={self._id!r}, name={self._name.value!r}, range={self._count_range})"


@dataclass(slots=True, eq=False, repr=False)
class CompetitionRegulation:
    """A published version of the competition regulations.

    A competition accrues one or more versions over time; each is an immutable
    published artefact (title, version label, publication date, file reference).
    Correcting a regulation means publishing a *new* version, not editing one.
    """

    _id: RegulationId
    _title: RegulationTitle
    _version: RegulationVersion
    _publication_date: date
    _file: FileReference

    @classmethod
    def create(
        cls,
        *,
        regulation_id: RegulationId,
        title: RegulationTitle,
        version: RegulationVersion,
        publication_date: date,
        file: FileReference,
    ) -> CompetitionRegulation:
        return cls(_id=regulation_id, _title=title, _version=version, _publication_date=publication_date, _file=file)

    @classmethod
    def rehydrate(
        cls,
        *,
        regulation_id: RegulationId,
        title: RegulationTitle,
        version: RegulationVersion,
        publication_date: date,
        file: FileReference,
    ) -> CompetitionRegulation:
        # A regulation is immutable, so reconstruction is identical to creation.
        return cls(_id=regulation_id, _title=title, _version=version, _publication_date=publication_date, _file=file)

    @property
    def id(self) -> RegulationId:
        return self._id

    @property
    def title(self) -> RegulationTitle:
        return self._title

    @property
    def version(self) -> RegulationVersion:
        return self._version

    @property
    def publication_date(self) -> date:
        return self._publication_date

    @property
    def file(self) -> FileReference:
        return self._file

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompetitionRegulation) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"CompetitionRegulation(id={self._id!r}, version={self._version.value!r})"


def _validate_sort_order(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidSortOrderError("Sort order must be an integer.")
    if value < 0:
        raise InvalidSortOrderError(f"Sort order must be non-negative, got {value}.")
    return value


def _validate_type_method_consistency(
    age_category_type: AgeCategoryType,
    mixed_calculation_method: MixedAgeCalculationMethod | None,
) -> None:
    """MIXED requires a method; STANDARD requires method is None."""
    if age_category_type is AgeCategoryType.MIXED and mixed_calculation_method is None:
        raise ValueError("mixed_calculation_method is required when type is MIXED.")
    if age_category_type is AgeCategoryType.STANDARD and mixed_calculation_method is not None:
        raise ValueError("mixed_calculation_method must be null when type is STANDARD.")


@dataclass(slots=True, eq=False, repr=False)
class CompetitionDocument:
    """An arbitrary organizer-uploaded document (regulations, memo, schedule, …).

    Documents are content, not admissibility configuration: they carry a category,
    a visibility, a sort order, and a published flag, and can be edited or
    (un)published independently of the competition's DRAFT/PUBLISHED status.
    """

    _id: DocumentId
    _title: DocumentTitle
    _category: DocumentCategory
    _visibility: DocumentVisibility
    _file: FileReference
    _description: DocumentDescription | None = None
    _sort_order: int = 0
    _published: bool = False

    @classmethod
    def create(
        cls,
        *,
        document_id: DocumentId,
        title: DocumentTitle,
        category: DocumentCategory,
        visibility: DocumentVisibility,
        file: FileReference,
        description: DocumentDescription | None = None,
        sort_order: int = 0,
        published: bool = False,
    ) -> CompetitionDocument:
        return cls(
            _id=document_id,
            _title=title,
            _category=category,
            _visibility=visibility,
            _file=file,
            _description=description,
            _sort_order=_validate_sort_order(sort_order),
            _published=published,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        document_id: DocumentId,
        title: DocumentTitle,
        category: DocumentCategory,
        visibility: DocumentVisibility,
        file: FileReference,
        description: DocumentDescription | None = None,
        sort_order: int = 0,
        published: bool = False,
    ) -> CompetitionDocument:
        return cls(
            _id=document_id,
            _title=title,
            _category=category,
            _visibility=visibility,
            _file=file,
            _description=description,
            _sort_order=sort_order,
            _published=published,
        )

    @property
    def id(self) -> DocumentId:
        return self._id

    @property
    def title(self) -> DocumentTitle:
        return self._title

    @property
    def category(self) -> DocumentCategory:
        return self._category

    @property
    def visibility(self) -> DocumentVisibility:
        return self._visibility

    @property
    def file(self) -> FileReference:
        return self._file

    @property
    def description(self) -> DocumentDescription | None:
        return self._description

    @property
    def sort_order(self) -> int:
        return self._sort_order

    @property
    def is_published(self) -> bool:
        return self._published

    def update(
        self,
        *,
        title: DocumentTitle,
        category: DocumentCategory,
        visibility: DocumentVisibility,
        file: FileReference,
        description: DocumentDescription | None,
        sort_order: int,
    ) -> None:
        self._title = title
        self._category = category
        self._visibility = visibility
        self._file = file
        self._description = description
        self._sort_order = _validate_sort_order(sort_order)

    def publish(self) -> None:
        self._published = True

    def unpublish(self) -> None:
        self._published = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompetitionDocument) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"CompetitionDocument(id={self._id!r}, title={self._title.value!r}, published={self._published})"


@dataclass(slots=True, eq=False, repr=False)
class AdditionalService:
    """An optional paid service (extra diploma, medal, video recording, shipping, …).

    Its price is a **fixed** amount — unlike a pricing rule it is *not* multiplied by
    the number of participants. ``enabled`` toggles whether the service is currently
    offered without deleting its configuration.
    """

    _id: ServiceId
    _name: ServiceName
    _price: Money
    _description: ServiceDescription | None = None
    _enabled: bool = True

    @classmethod
    def create(
        cls,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        description: ServiceDescription | None = None,
        enabled: bool = True,
    ) -> AdditionalService:
        return cls(_id=service_id, _name=name, _price=price, _description=description, _enabled=enabled)

    @classmethod
    def rehydrate(
        cls,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        description: ServiceDescription | None = None,
        enabled: bool = True,
    ) -> AdditionalService:
        return cls(_id=service_id, _name=name, _price=price, _description=description, _enabled=enabled)

    @property
    def id(self) -> ServiceId:
        return self._id

    @property
    def name(self) -> ServiceName:
        return self._name

    @property
    def price(self) -> Money:
        return self._price

    @property
    def description(self) -> ServiceDescription | None:
        return self._description

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def update(self, *, name: ServiceName, price: Money, description: ServiceDescription | None) -> None:
        self._name = name
        self._price = price
        self._description = description

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AdditionalService) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"AdditionalService(id={self._id!r}, name={self._name.value!r}, enabled={self._enabled})"


@dataclass(slots=True, eq=False, repr=False)
class Contact:
    """An official competition contact on one channel (phone, email, Telegram, …).

    Exactly one contact in a competition is the *primary* one; the root maintains
    that invariant. The value is stored opaquely (see :class:`ContactValue`).
    """

    _id: ContactId
    _type: ContactType
    _value: ContactValue
    _is_primary: bool = False

    @classmethod
    def create(cls, *, contact_id: ContactId, contact_type: ContactType, value: ContactValue, is_primary: bool = False) -> Contact:
        return cls(_id=contact_id, _type=contact_type, _value=value, _is_primary=is_primary)

    @classmethod
    def rehydrate(cls, *, contact_id: ContactId, contact_type: ContactType, value: ContactValue, is_primary: bool = False) -> Contact:
        return cls(_id=contact_id, _type=contact_type, _value=value, _is_primary=is_primary)

    @property
    def id(self) -> ContactId:
        return self._id

    @property
    def type(self) -> ContactType:
        return self._type

    @property
    def value(self) -> ContactValue:
        return self._value

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    def mark_primary(self) -> None:
        self._is_primary = True

    def unmark_primary(self) -> None:
        self._is_primary = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Contact) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Contact(id={self._id!r}, type={self._type}, primary={self._is_primary})"


@dataclass(slots=True, eq=False, repr=False)
class InformationBlock:
    """A configurable block of public information (arrival, accommodation, FAQ, …).

    Sections are **not** hardcoded: an organizer composes any number of titled
    blocks of :class:`RichText` content, each independently (un)published and
    ordered. Block titles are unique within a competition.
    """

    _id: InformationBlockId
    _title: InformationBlockTitle
    _content: RichText
    _published: bool = False
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        block_id: InformationBlockId,
        title: InformationBlockTitle,
        content: RichText,
        published: bool = False,
        sort_order: int = 0,
    ) -> InformationBlock:
        return cls(_id=block_id, _title=title, _content=content, _published=published, _sort_order=_validate_sort_order(sort_order))

    @classmethod
    def rehydrate(
        cls,
        *,
        block_id: InformationBlockId,
        title: InformationBlockTitle,
        content: RichText,
        published: bool = False,
        sort_order: int = 0,
    ) -> InformationBlock:
        return cls(_id=block_id, _title=title, _content=content, _published=published, _sort_order=sort_order)

    @property
    def id(self) -> InformationBlockId:
        return self._id

    @property
    def title(self) -> InformationBlockTitle:
        return self._title

    @property
    def content(self) -> RichText:
        return self._content

    @property
    def is_published(self) -> bool:
        return self._published

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def edit(self, *, title: InformationBlockTitle, content: RichText, sort_order: int) -> None:
        self._title = title
        self._content = content
        self._sort_order = _validate_sort_order(sort_order)

    def publish(self) -> None:
        self._published = True

    def hide(self) -> None:
        self._published = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InformationBlock) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"InformationBlock(id={self._id!r}, title={self._title.value!r}, published={self._published})"


# ===========================================================================
# Aggregate root
# ===========================================================================


@dataclass(slots=True, eq=False, repr=False)
class Competition:
    """The Competition aggregate root — a configurable competition constructor.

    Guards its full lifecycle (``DRAFT → CONFIGURED → READY → PUBLISHED →
    REGISTRATION_OPEN → REGISTRATION_CLOSED → RUNNING → COMPLETED``, plus
    ``ARCHIVED`` from any state) and every cross-element invariant of its
    configuration. Equality/hashing is by :class:`CompetitionId`.
    """

    _token: InitVar[object]
    _id: CompetitionId
    _title: CompetitionTitle
    _season: Season
    _organizer_id: OrganizerId
    _status: CompetitionStatus
    _created_at: datetime
    _updated_at: datetime
    _description: CompetitionDescription | None = None
    _branding: CompetitionBranding = field(default_factory=CompetitionBranding.empty)
    _venue: Venue | None = None
    _registration_period: DateRange | None = None
    _competition_period: DateRange | None = None
    _deadlines: RegistrationDeadlines = field(default_factory=RegistrationDeadlines)
    _settings: CompetitionSettings = field(default_factory=CompetitionSettings.default)
    _categories: dict[CategoryId, Category] = field(default_factory=dict)
    _disciplines: dict[DisciplineId, Discipline] = field(default_factory=dict)
    _age_categories: dict[AgeCategoryId, AgeCategory] = field(default_factory=dict)
    _participant_groups: dict[ParticipantGroupId, ParticipantGroup] = field(default_factory=dict)
    _formats: set[ParticipationFormat] = field(default_factory=set)
    _admission_rules: dict[AdmissionCombination, AdmissionRule] = field(default_factory=dict)
    _pricing_rules: dict[AdmissionCombination, PricingRule] = field(default_factory=dict)
    _regulations: dict[RegulationId, CompetitionRegulation] = field(default_factory=dict)
    _current_regulation_id: RegulationId | None = None
    _documents: dict[DocumentId, CompetitionDocument] = field(default_factory=dict)
    _additional_services: dict[ServiceId, AdditionalService] = field(default_factory=dict)
    _contacts: dict[ContactId, Contact] = field(default_factory=dict)
    _information_blocks: dict[InformationBlockId, InformationBlock] = field(default_factory=dict)
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "Competition must be created via Competition.draft() or Competition.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def draft(
        cls,
        *,
        competition_id: CompetitionId,
        title: CompetitionTitle,
        season: Season,
        organizer_id: OrganizerId,
        now: datetime,
        description: CompetitionDescription | None = None,
        logo: FileReference | None = None,
        banner: FileReference | None = None,
        poster: FileReference | None = None,
        venue: Venue | None = None,
        registration_period: DateRange | None = None,
        competition_period: DateRange | None = None,
        settings: CompetitionSettings | None = None,
        deadlines: RegistrationDeadlines | None = None,
    ) -> tuple[Competition, list[DomainEvent]]:
        """Create a brand-new competition in the DRAFT state.

        The only construction path for a new competition. Its configuration
        (categories, disciplines, rules, pricing, …) starts empty and is built up
        with the ``add_*`` methods before :meth:`publish`.
        """
        competition = cls(
            _token=_CREATION_TOKEN,
            _id=competition_id,
            _title=title,
            _season=season,
            _organizer_id=organizer_id,
            _status=CompetitionStatus.DRAFT,
            _created_at=now,
            _updated_at=now,
            _description=description,
            _branding=CompetitionBranding(logo=logo, banner=banner, poster=poster),
            _venue=venue,
            _registration_period=registration_period,
            _competition_period=competition_period,
            _settings=settings if settings is not None else CompetitionSettings.default(),
            _deadlines=deadlines if deadlines is not None else RegistrationDeadlines(),
        )
        event = CompetitionCreated(aggregate_id=competition_id.value, title=title, season=season, organizer_id=organizer_id)
        return competition, [event]

    @classmethod
    def rehydrate(
        cls,
        *,
        competition_id: CompetitionId,
        title: CompetitionTitle,
        season: Season,
        organizer_id: OrganizerId,
        status: CompetitionStatus,
        created_at: datetime,
        updated_at: datetime,
        description: CompetitionDescription | None = None,
        logo: FileReference | None = None,
        banner: FileReference | None = None,
        poster: FileReference | None = None,
        branding: CompetitionBranding | None = None,
        venue: Venue | None = None,
        registration_period: DateRange | None = None,
        competition_period: DateRange | None = None,
        settings: CompetitionSettings | None = None,
        deadlines: RegistrationDeadlines | None = None,
        categories: Sequence[Category] = (),
        disciplines: Sequence[Discipline] = (),
        age_categories: Sequence[AgeCategory] = (),
        participant_groups: Sequence[ParticipantGroup] = (),
        formats: Iterable[ParticipationFormat] = (),
        admission_rules: Sequence[AdmissionRule] = (),
        pricing_rules: Sequence[PricingRule] = (),
        regulations: Sequence[CompetitionRegulation] = (),
        current_regulation_id: RegulationId | None = None,
        documents: Sequence[CompetitionDocument] = (),
        additional_services: Sequence[AdditionalService] = (),
        contacts: Sequence[Contact] = (),
        information_blocks: Sequence[InformationBlock] = (),
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Competition:
        """Reconstruct the aggregate from persistence (no re-validation, no events).

        ``branding`` may be supplied directly or assembled from ``logo``/``banner``/
        ``poster`` (kept for backward compatibility).
        """
        return cls(
            _token=_CREATION_TOKEN,
            _id=competition_id,
            _title=title,
            _season=season,
            _organizer_id=organizer_id,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _description=description,
            _branding=branding if branding is not None else CompetitionBranding(logo=logo, banner=banner, poster=poster),
            _venue=venue,
            _registration_period=registration_period,
            _competition_period=competition_period,
            _settings=settings if settings is not None else CompetitionSettings.default(),
            _deadlines=deadlines if deadlines is not None else RegistrationDeadlines(),
            _categories={c.id: c for c in categories},
            _disciplines={d.id: d for d in disciplines},
            _age_categories={a.id: a for a in age_categories},
            _participant_groups={g.id: g for g in participant_groups},
            _formats=set(formats),
            _admission_rules={r.combination: r for r in admission_rules},
            _pricing_rules={p.combination: p for p in pricing_rules},
            _regulations={r.id: r for r in regulations},
            _current_regulation_id=current_regulation_id,
            _documents={d.id: d for d in documents},
            _additional_services={s.id: s for s in additional_services},
            _contacts={c.id: c for c in contacts},
            _information_blocks={b.id: b for b in information_blocks},
            _deleted_at=deleted_at,
            _version=version,
        )

    @classmethod
    def from_template(
        cls,
        *,
        competition_id: CompetitionId,
        title: CompetitionTitle,
        season: Season,
        organizer_id: OrganizerId,
        template: CompetitionTemplate,
        now: datetime,
        description: CompetitionDescription | None = None,
        logo: FileReference | None = None,
        banner: FileReference | None = None,
        venue: Venue | None = None,
        registration_period: DateRange | None = None,
        competition_period: DateRange | None = None,
    ) -> tuple[Competition, list[DomainEvent]]:
        """Create a DRAFT competition pre-populated from a reusable ``template``.

        The template's taxonomy, formats, admission and pricing rules are **cloned
        with fresh identities** (so the new competition owns its own child ids while
        preserving all internal references). The template was validated when it was
        assembled, so no re-validation is needed here. Regulations, documents and
        additional services are competition-specific and are **not** copied.
        """
        competition, events = cls.draft(
            competition_id=competition_id,
            title=title,
            season=season,
            organizer_id=organizer_id,
            now=now,
            description=description,
            logo=logo,
            banner=banner,
            venue=venue,
            registration_period=registration_period,
            competition_period=competition_period,
        )
        competition._populate_from_template(template)
        return competition, events

    def _populate_from_template(self, template: CompetitionTemplate) -> None:
        """Copy ``template``'s configuration into this fresh draft, remapping ids."""
        category_map: dict[CategoryId, CategoryId] = {}
        discipline_map: dict[DisciplineId, DisciplineId] = {}
        age_map: dict[AgeCategoryId, AgeCategoryId] = {}
        group_map: dict[ParticipantGroupId, ParticipantGroupId] = {}

        for category in template.categories:
            new_category_id = CategoryId.generate()
            category_map[category.id] = new_category_id
            self._categories[new_category_id] = Category.create(
                category_id=new_category_id,
                name=category.name,
                description=category.description,
                sort_order=category.sort_order,
            )
        for discipline in template.disciplines:
            new_discipline_id = DisciplineId.generate()
            discipline_map[discipline.id] = new_discipline_id
            self._disciplines[new_discipline_id] = Discipline.create(
                discipline_id=new_discipline_id,
                category_id=category_map[discipline.category_id],
                name=discipline.name,
                sort_order=discipline.sort_order,
            )
        for age_category in template.age_categories:
            new_age_id = AgeCategoryId.generate()
            age_map[age_category.id] = new_age_id
            self._age_categories[new_age_id] = AgeCategory.create(
                age_category_id=new_age_id,
                category_id=category_map[age_category.category_id],
                name=age_category.name,
                age_range=age_category.age_range,
                age_category_type=age_category.type,
                mixed_calculation_method=age_category.mixed_calculation_method,
                sort_order=age_category.sort_order,
            )
        for group in template.participant_groups:
            new_group_id = ParticipantGroupId.generate()
            group_map[group.id] = new_group_id
            self._participant_groups[new_group_id] = ParticipantGroup.create(
                participant_group_id=new_group_id,
                category_id=category_map[group.category_id],
                name=group.name,
                count_range=group.count_range,
                description=group.description,
                sort_order=group.sort_order,
            )
        self._formats.update(template.participation_formats)

        def _remap(combination: AdmissionCombination) -> AdmissionCombination:
            return AdmissionCombination(
                category_id=category_map[combination.category_id],
                discipline_id=discipline_map[combination.discipline_id],
                age_category_id=age_map[combination.age_category_id],
                participant_group_id=group_map[combination.participant_group_id],
                participation_format=combination.participation_format,
            )

        for rule in template.admission_rules:
            remapped = _remap(rule.combination)
            self._admission_rules[remapped] = AdmissionRule(combination=remapped)
        for pricing in template.pricing_rules:
            remapped = _remap(pricing.combination)
            self._pricing_rules[remapped] = PricingRule(combination=remapped, price_per_participant=pricing.price_per_participant)

    # ------------------------------------------------------------------
    # Properties (read-only views)
    # ------------------------------------------------------------------

    @property
    def id(self) -> CompetitionId:
        return self._id

    @property
    def title(self) -> CompetitionTitle:
        return self._title

    @property
    def season(self) -> Season:
        return self._season

    @property
    def organizer_id(self) -> OrganizerId:
        return self._organizer_id

    @property
    def status(self) -> CompetitionStatus:
        return self._status

    @property
    def description(self) -> CompetitionDescription | None:
        return self._description

    @property
    def branding(self) -> CompetitionBranding:
        return self._branding

    @property
    def logo(self) -> FileReference | None:
        return self._branding.logo

    @property
    def banner(self) -> FileReference | None:
        return self._branding.banner

    @property
    def poster(self) -> FileReference | None:
        return self._branding.poster

    @property
    def settings(self) -> CompetitionSettings:
        return self._settings

    @property
    def deadlines(self) -> RegistrationDeadlines:
        return self._deadlines

    @property
    def contacts(self) -> tuple[Contact, ...]:
        return tuple(self._contacts.values())

    @property
    def primary_contact(self) -> Contact | None:
        """The single contact marked primary, or ``None`` if there are no contacts."""
        return next((c for c in self._contacts.values() if c.is_primary), None)

    @property
    def information_blocks(self) -> tuple[InformationBlock, ...]:
        return tuple(self._information_blocks.values())

    @property
    def venue(self) -> Venue | None:
        return self._venue

    @property
    def registration_period(self) -> DateRange | None:
        return self._registration_period

    @property
    def competition_period(self) -> DateRange | None:
        return self._competition_period

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def categories(self) -> tuple[Category, ...]:
        return tuple(self._categories.values())

    @property
    def disciplines(self) -> tuple[Discipline, ...]:
        return tuple(self._disciplines.values())

    @property
    def age_categories(self) -> tuple[AgeCategory, ...]:
        return tuple(self._age_categories.values())

    @property
    def participant_groups(self) -> tuple[ParticipantGroup, ...]:
        return tuple(self._participant_groups.values())

    @property
    def participation_formats(self) -> frozenset[ParticipationFormat]:
        return frozenset(self._formats)

    @property
    def admission_rules(self) -> tuple[AdmissionRule, ...]:
        return tuple(self._admission_rules.values())

    @property
    def pricing_rules(self) -> tuple[PricingRule, ...]:
        return tuple(self._pricing_rules.values())

    @property
    def regulations(self) -> tuple[CompetitionRegulation, ...]:
        return tuple(self._regulations.values())

    @property
    def documents(self) -> tuple[CompetitionDocument, ...]:
        return tuple(self._documents.values())

    @property
    def additional_services(self) -> tuple[AdditionalService, ...]:
        return tuple(self._additional_services.values())

    @property
    def current_regulation(self) -> CompetitionRegulation | None:
        """The single current regulation version, or ``None`` if none published yet."""
        if self._current_regulation_id is None:
            return None
        return self._regulations.get(self._current_regulation_id)

    def is_draft(self) -> bool:
        return self._status is CompetitionStatus.DRAFT

    def is_published(self) -> bool:
        return self._status is CompetitionStatus.PUBLISHED

    def is_archived(self) -> bool:
        return self._status is CompetitionStatus.ARCHIVED

    def is_registration_open(self) -> bool:
        return self._status is CompetitionStatus.REGISTRATION_OPEN

    def disciplines_of(self, category_id: CategoryId) -> tuple[Discipline, ...]:
        """All disciplines belonging to ``category_id``."""
        return tuple(d for d in self._disciplines.values() if d.category_id == category_id)

    def age_categories_of(self, category_id: CategoryId) -> tuple[AgeCategory, ...]:
        """All age categories belonging to ``category_id``."""
        return tuple(a for a in self._age_categories.values() if a.category_id == category_id)

    def participant_groups_of(self, category_id: CategoryId) -> tuple[ParticipantGroup, ...]:
        """All participant groups belonging to ``category_id``."""
        return tuple(g for g in self._participant_groups.values() if g.category_id == category_id)

    # ------------------------------------------------------------------
    # Admissibility & pricing queries
    # ------------------------------------------------------------------

    def is_admissible(self, combination: AdmissionCombination) -> bool:
        """Whether an application may be created for ``combination``.

        The gate for the future Applications context: no admission rule ⇒ not
        admissible. Only checks rule presence — reference validity is guaranteed
        at configuration time.
        """
        return combination in self._admission_rules

    def price_for(self, combination: AdmissionCombination) -> Money | None:
        """The price per participant for ``combination``, or ``None`` if unpriced."""
        rule = self._pricing_rules.get(combination)
        return rule.price_per_participant if rule is not None else None

    # ------------------------------------------------------------------
    # Deadline queries (answer "is X still allowed at `now`?")
    # ------------------------------------------------------------------
    #
    # These answer the *deadline* question only (and refuse everything once
    # archived). Layering admission/lifecycle policy on top is the Application
    # context's job; the Competition merely owns the authoritative cut-off dates.

    def is_application_allowed(self, now: datetime) -> bool:
        return not self.is_archived() and self._deadlines.is_open(DeadlineKind.APPLICATION, now)

    def is_payment_allowed(self, now: datetime) -> bool:
        return not self.is_archived() and self._deadlines.is_open(DeadlineKind.PAYMENT, now)

    def is_music_upload_allowed(self, now: datetime) -> bool:
        return not self.is_archived() and self._deadlines.is_open(DeadlineKind.MUSIC_UPLOAD, now)

    def is_document_upload_allowed(self, now: datetime) -> bool:
        return not self.is_archived() and self._deadlines.is_open(DeadlineKind.DOCUMENT_UPLOAD, now)

    def is_correction_allowed(self, now: datetime) -> bool:
        return not self.is_archived() and self._deadlines.is_open(DeadlineKind.CORRECTION, now)

    # ------------------------------------------------------------------
    # General information
    # ------------------------------------------------------------------

    def update_general_information(
        self,
        *,
        now: datetime,
        title: CompetitionTitle,
        season: Season,
        description: CompetitionDescription | None = None,
        logo: FileReference | None = None,
        banner: FileReference | None = None,
        venue: Venue | None = None,
        registration_period: DateRange | None = None,
        competition_period: DateRange | None = None,
    ) -> list[DomainEvent]:
        """Replace the competition's general information (allowed unless ARCHIVED).

        General information is presentation, not admissibility configuration, so it
        may be edited even after publication — it cannot invalidate an application.
        """
        self._ensure_not_archived()
        self._title = title
        self._season = season
        self._description = description
        # Logo/banner are branding assets; update them via branding, preserving the poster.
        self._branding = CompetitionBranding(logo=logo, banner=banner, poster=self._branding.poster)
        self._venue = venue
        self._registration_period = registration_period
        self._competition_period = competition_period
        self._touch(now)
        return [CompetitionGeneralInformationUpdated(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Taxonomy configuration (DRAFT-only)
    # ------------------------------------------------------------------

    def add_category(
        self,
        *,
        category_id: CategoryId,
        name: CategoryName,
        now: datetime,
        description: CategoryDescription | None = None,
        sort_order: int | None = None,
    ) -> Category:
        """Add a category. Names are unique within the competition."""
        self._ensure_configurable()
        if any(c.name == name for c in self._categories.values()):
            raise DuplicateCategoryError(f"A category named {name.value!r} already exists.")
        if sort_order is None:
            sort_order = self._next_category_sort_order()
        category = Category.create(category_id=category_id, name=name, description=description, sort_order=sort_order)
        self._categories[category_id] = category
        self._touch(now)
        return category

    def rename_category(
        self,
        *,
        category_id: CategoryId,
        now: datetime,
        name: CategoryName | None = None,
        description: CategoryDescription | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        self._ensure_configurable()
        category = self._require_category(category_id)
        if name is not None and any(cid != category_id and c.name == name for cid, c in self._categories.items()):
            raise DuplicateCategoryError(f"A category named {name.value!r} already exists.")
        category.update(name=name, description=description, sort_order=sort_order)
        self._touch(now)

    def remove_category(self, *, category_id: CategoryId, now: datetime) -> None:
        """Remove a category. Refused while any discipline, group, age category, or rule references it."""
        self._ensure_configurable()
        self._require_category(category_id)
        if any(d.category_id == category_id for d in self._disciplines.values()):
            raise CategoryInUseError("The category still has disciplines.")
        if any(a.category_id == category_id for a in self._age_categories.values()):
            raise CategoryInUseError("The category still has age categories.")
        if any(g.category_id == category_id for g in self._participant_groups.values()):
            raise CategoryInUseError("The category still has participant groups.")
        if any(c.category_id == category_id for c in self._admission_rules):
            raise CategoryInUseError("The category is referenced by admission rules.")
        if any(c.category_id == category_id for c in self._pricing_rules):
            raise CategoryInUseError("The category is referenced by pricing rules.")
        del self._categories[category_id]
        self._touch(now)

    def add_discipline(
        self,
        *,
        discipline_id: DisciplineId,
        category_id: CategoryId,
        name: DisciplineName,
        now: datetime,
        sort_order: int | None = None,
    ) -> Discipline:
        """Add a discipline to a category. Names are unique within that category."""
        self._ensure_configurable()
        self._require_category(category_id)
        if any(d.category_id == category_id and d.name == name for d in self._disciplines.values()):
            raise DuplicateDisciplineError(f"A discipline named {name.value!r} already exists in this category.")
        if sort_order is None:
            sort_order = self._next_discipline_sort_order(category_id)
        discipline = Discipline.create(discipline_id=discipline_id, category_id=category_id, name=name, sort_order=sort_order)
        self._disciplines[discipline_id] = discipline
        self._touch(now)
        return discipline

    def rename_discipline(
        self,
        *,
        discipline_id: DisciplineId,
        now: datetime,
        name: DisciplineName | None = None,
        sort_order: int | None = None,
    ) -> None:
        self._ensure_configurable()
        discipline = self._require_discipline(discipline_id)
        if name is not None and any(
            did != discipline_id and d.category_id == discipline.category_id and d.name == name for did, d in self._disciplines.items()
        ):
            raise DuplicateDisciplineError(f"A discipline named {name.value!r} already exists in this category.")
        discipline.update(name=name, sort_order=sort_order)
        self._touch(now)

    def remove_discipline(self, *, discipline_id: DisciplineId, now: datetime) -> None:
        self._ensure_configurable()
        self._require_discipline(discipline_id)
        if any(c.discipline_id == discipline_id for c in self._admission_rules):
            raise DisciplineInUseError("The discipline is referenced by admission rules.")
        if any(c.discipline_id == discipline_id for c in self._pricing_rules):
            raise DisciplineInUseError("The discipline is referenced by pricing rules.")
        del self._disciplines[discipline_id]
        self._touch(now)

    def add_age_category(
        self,
        *,
        age_category_id: AgeCategoryId,
        category_id: CategoryId,
        name: AgeCategoryName,
        age_range: AgeRange,
        now: datetime,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int | None = None,
    ) -> AgeCategory:
        """Add an age band to a nomination. Overlapping ranges are refused within the nomination."""
        self._ensure_configurable()
        self._require_category(category_id)
        ensure_age_range_free(self._age_categories, age_range, category_id=category_id)
        if any(a.category_id == category_id and a.name == name for a in self._age_categories.values()):
            raise DuplicateAgeCategoryNameError(f"An age category named {name.value!r} already exists in this nomination.")
        if sort_order is None:
            sort_order = self._next_age_category_sort_order(category_id)
        age_category = AgeCategory.create(
            age_category_id=age_category_id,
            category_id=category_id,
            name=name,
            age_range=age_range,
            age_category_type=age_category_type,
            mixed_calculation_method=mixed_calculation_method,
            sort_order=sort_order,
        )
        self._age_categories[age_category_id] = age_category
        self._touch(now)
        return age_category

    def update_age_category(
        self,
        *,
        age_category_id: AgeCategoryId,
        now: datetime,
        name: AgeCategoryName | None = None,
        age_range: AgeRange | None = None,
        age_category_type: AgeCategoryType | None = None,
        mixed_calculation_method: MixedAgeCalculationMethod | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        """Partial update of an age category (name, age_range, type, method, sort_order)."""
        self._ensure_configurable()
        age_category = self._require_age_category(age_category_id)
        cat_id = age_category.category_id
        if name is not None and any(
            aid != age_category_id and a.category_id == cat_id and a.name == name for aid, a in self._age_categories.items()
        ):
            raise DuplicateAgeCategoryNameError(f"An age category named {name.value!r} already exists in this nomination.")
        if age_range is not None:
            ensure_age_range_free(self._age_categories, age_range, category_id=cat_id, exclude=age_category_id)
        age_category.update(
            name=name,
            age_range=age_range,
            age_category_type=age_category_type,
            mixed_calculation_method=mixed_calculation_method,
            sort_order=sort_order,
        )
        self._touch(now)

    def remove_age_category(self, *, age_category_id: AgeCategoryId, now: datetime) -> None:
        self._ensure_configurable()
        self._require_age_category(age_category_id)
        if any(c.age_category_id == age_category_id for c in self._admission_rules):
            raise AgeCategoryInUseError("The age category is referenced by admission rules.")
        if any(c.age_category_id == age_category_id for c in self._pricing_rules):
            raise AgeCategoryInUseError("The age category is referenced by pricing rules.")
        del self._age_categories[age_category_id]
        self._touch(now)

    def add_participant_group(
        self,
        *,
        participant_group_id: ParticipantGroupId,
        category_id: CategoryId,
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        now: datetime,
        description: ParticipantGroupDescription | None = None,
        sort_order: int | None = None,
    ) -> ParticipantGroup:
        """Add a participant group to a category.

        Names are unique within the category, and count ranges must not overlap
        another group's range in the same category (each headcount maps to one group).
        """
        self._ensure_configurable()
        self._require_category(category_id)
        if any(g.category_id == category_id and g.name == name for g in self._participant_groups.values()):
            raise DuplicateParticipantGroupError(f"A participant group named {name.value!r} already exists in this category.")
        ensure_participant_range_free(self._participant_groups, category_id, count_range)
        if sort_order is None:
            sort_order = self._next_participant_group_sort_order(category_id)
        group = ParticipantGroup.create(
            participant_group_id=participant_group_id,
            category_id=category_id,
            name=name,
            count_range=count_range,
            description=description,
            sort_order=sort_order,
        )
        self._participant_groups[participant_group_id] = group
        self._touch(now)
        return group

    def update_participant_group(
        self,
        *,
        participant_group_id: ParticipantGroupId,
        now: datetime,
        name: ParticipantGroupName | None = None,
        count_range: ParticipantCountRange | None = None,
        description: ParticipantGroupDescription | None = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        """Partial update of a participant group (name, range, description, sort_order)."""
        self._ensure_configurable()
        group = self._require_participant_group(participant_group_id)
        cat_id = group.category_id
        if name is not None and any(
            gid != participant_group_id and g.category_id == cat_id and g.name == name for gid, g in self._participant_groups.items()
        ):
            raise DuplicateParticipantGroupError(f"A participant group named {name.value!r} already exists in this category.")
        if count_range is not None:
            ensure_participant_range_free(self._participant_groups, cat_id, count_range, exclude=participant_group_id)
        group.update(
            name=name,
            count_range=count_range,
            description=description,
            sort_order=sort_order,
        )
        self._touch(now)

    def remove_participant_group(self, *, participant_group_id: ParticipantGroupId, now: datetime) -> None:
        self._ensure_configurable()
        self._require_participant_group(participant_group_id)
        if any(c.participant_group_id == participant_group_id for c in self._admission_rules):
            raise ParticipantGroupInUseError("The participant group is referenced by admission rules.")
        if any(c.participant_group_id == participant_group_id for c in self._pricing_rules):
            raise ParticipantGroupInUseError("The participant group is referenced by pricing rules.")
        del self._participant_groups[participant_group_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Participation formats (DRAFT-only)
    # ------------------------------------------------------------------

    def enable_format(self, *, participation_format: ParticipationFormat, now: datetime) -> list[DomainEvent]:
        self._ensure_configurable()
        if participation_format in self._formats:
            return []
        self._formats.add(participation_format)
        self._touch(now)
        return [ParticipationFormatEnabled(aggregate_id=self._id.value, participation_format=participation_format)]

    def disable_format(self, *, participation_format: ParticipationFormat, now: datetime) -> list[DomainEvent]:
        self._ensure_configurable()
        if any(c.participation_format is participation_format for c in self._admission_rules):
            raise ParticipationFormatInUseError("The format is referenced by admission rules.")
        if any(c.participation_format is participation_format for c in self._pricing_rules):
            raise ParticipationFormatInUseError("The format is referenced by pricing rules.")
        if participation_format not in self._formats:
            return []
        self._formats.discard(participation_format)
        self._touch(now)
        return [ParticipationFormatDisabled(aggregate_id=self._id.value, participation_format=participation_format)]

    # ------------------------------------------------------------------
    # Admission & pricing rules (DRAFT-only)
    # ------------------------------------------------------------------

    def add_admission_rule(self, *, combination: AdmissionCombination, now: datetime) -> list[DomainEvent]:
        """Allow ``combination``. Every referenced element must exist and be consistent."""
        self._ensure_configurable()
        self._validate_combination(combination)
        if combination in self._admission_rules:
            raise DuplicateAdmissionRuleError("An admission rule for this combination already exists.")
        self._admission_rules[combination] = AdmissionRule(combination=combination)
        self._touch(now)
        return [
            AdmissionRuleAdded(
                aggregate_id=self._id.value,
                category_id=combination.category_id,
                discipline_id=combination.discipline_id,
                age_category_id=combination.age_category_id,
                participant_group_id=combination.participant_group_id,
                participation_format=combination.participation_format,
            )
        ]

    def remove_admission_rule(self, *, combination: AdmissionCombination, now: datetime) -> list[DomainEvent]:
        """Remove an admission rule. Refused while a pricing rule prices the same combination."""
        self._ensure_configurable()
        if combination not in self._admission_rules:
            raise AdmissionRuleNotFoundError("No admission rule exists for this combination.")
        if combination in self._pricing_rules:
            raise AdmissionRuleInUseError("A pricing rule prices this combination; remove the price first.")
        del self._admission_rules[combination]
        self._touch(now)
        return [
            AdmissionRuleRemoved(
                aggregate_id=self._id.value,
                category_id=combination.category_id,
                discipline_id=combination.discipline_id,
                age_category_id=combination.age_category_id,
                participant_group_id=combination.participant_group_id,
                participation_format=combination.participation_format,
            )
        ]

    def add_pricing_rule(self, *, combination: AdmissionCombination, price_per_participant: Money, now: datetime) -> list[DomainEvent]:
        """Set the per-participant price for a combination. Requires an admission rule to exist."""
        self._ensure_configurable()
        self._validate_combination(combination)
        if combination not in self._admission_rules:
            raise AdmissionRuleNotFoundError("Cannot price a combination that is not admissible.")
        if combination in self._pricing_rules:
            raise DuplicatePricingRuleError("A pricing rule for this combination already exists.")
        self._pricing_rules[combination] = PricingRule(combination=combination, price_per_participant=price_per_participant)
        self._touch(now)
        return [self._pricing_added_event(combination, price_per_participant)]

    def change_price(self, *, combination: AdmissionCombination, price_per_participant: Money, now: datetime) -> list[DomainEvent]:
        """Change the per-participant price of an existing pricing rule.

        Emits :class:`~apps.competitions.domain.events.PricingRuleAdded` — the event
        records that a price is now set for the combination, whether first set or changed.
        """
        self._ensure_configurable()
        if combination not in self._pricing_rules:
            raise PricingRuleNotFoundError("No pricing rule exists for this combination.")
        self._pricing_rules[combination] = PricingRule(combination=combination, price_per_participant=price_per_participant)
        self._touch(now)
        return [self._pricing_added_event(combination, price_per_participant)]

    def remove_pricing_rule(self, *, combination: AdmissionCombination, now: datetime) -> list[DomainEvent]:
        self._ensure_configurable()
        if combination not in self._pricing_rules:
            raise PricingRuleNotFoundError("No pricing rule exists for this combination.")
        del self._pricing_rules[combination]
        self._touch(now)
        return [
            PricingRuleRemoved(
                aggregate_id=self._id.value,
                category_id=combination.category_id,
                discipline_id=combination.discipline_id,
                age_category_id=combination.age_category_id,
                participant_group_id=combination.participant_group_id,
                participation_format=combination.participation_format,
            )
        ]

    # ------------------------------------------------------------------
    # Regulations (allowed unless ARCHIVED — content, not admissibility config)
    # ------------------------------------------------------------------

    def add_regulation(
        self,
        *,
        regulation_id: RegulationId,
        title: RegulationTitle,
        version: RegulationVersion,
        publication_date: date,
        file: FileReference,
        now: datetime,
    ) -> tuple[CompetitionRegulation, list[DomainEvent]]:
        """Publish a new version of the regulations and make it the current one.

        Previous versions stay available; only the pointer to the *current* version
        moves. Emits :class:`RegulationPublished`. Invariant: whenever at least one
        regulation exists, exactly one is current.
        """
        self._ensure_not_archived()
        regulation = CompetitionRegulation.create(
            regulation_id=regulation_id, title=title, version=version, publication_date=publication_date, file=file
        )
        self._regulations[regulation_id] = regulation
        self._current_regulation_id = regulation_id
        self._touch(now)
        event = RegulationPublished(
            aggregate_id=self._id.value, regulation_id=regulation_id, title=title, version=version, publication_date=publication_date
        )
        return regulation, [event]

    def make_regulation_current(self, *, regulation_id: RegulationId, now: datetime) -> None:
        """Promote an existing regulation version to be the current one."""
        self._ensure_not_archived()
        if regulation_id not in self._regulations:
            raise RegulationNotFoundError(f"No regulation {regulation_id} in this competition.")
        if self._current_regulation_id == regulation_id:
            return
        self._current_regulation_id = regulation_id
        self._touch(now)

    def remove_regulation(self, *, regulation_id: RegulationId, now: datetime) -> None:
        """Remove a regulation version, preserving the "exactly one current" invariant.

        Removing the current version promotes the most recently published remaining
        version; removing the last version clears the current pointer.
        """
        self._ensure_not_archived()
        if regulation_id not in self._regulations:
            raise RegulationNotFoundError(f"No regulation {regulation_id} in this competition.")
        del self._regulations[regulation_id]
        if self._current_regulation_id == regulation_id:
            self._current_regulation_id = self._latest_regulation_id()
        self._touch(now)

    def _latest_regulation_id(self) -> RegulationId | None:
        """The id of the most recently published remaining regulation, or ``None``."""
        if not self._regulations:
            return None
        latest = max(self._regulations.values(), key=lambda r: (r.publication_date, r.id.value.hex))
        return latest.id

    # ------------------------------------------------------------------
    # Documents (allowed unless ARCHIVED — content, not admissibility config)
    # ------------------------------------------------------------------

    def add_document(
        self,
        *,
        document_id: DocumentId,
        title: DocumentTitle,
        category: DocumentCategory,
        visibility: DocumentVisibility,
        file: FileReference,
        now: datetime,
        description: DocumentDescription | None = None,
        sort_order: int = 0,
        published: bool = False,
    ) -> CompetitionDocument:
        self._ensure_not_archived()
        document = CompetitionDocument.create(
            document_id=document_id,
            title=title,
            category=category,
            visibility=visibility,
            file=file,
            description=description,
            sort_order=sort_order,
            published=published,
        )
        self._documents[document_id] = document
        self._touch(now)
        return document

    def update_document(
        self,
        *,
        document_id: DocumentId,
        title: DocumentTitle,
        category: DocumentCategory,
        visibility: DocumentVisibility,
        file: FileReference,
        description: DocumentDescription | None,
        sort_order: int,
        now: datetime,
    ) -> None:
        self._ensure_not_archived()
        document = self._require_document(document_id)
        document.update(title=title, category=category, visibility=visibility, file=file, description=description, sort_order=sort_order)
        self._touch(now)

    def publish_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_document(document_id).publish()
        self._touch(now)

    def unpublish_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_document(document_id).unpublish()
        self._touch(now)

    def remove_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_document(document_id)
        del self._documents[document_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Additional services (optional paid extras; allowed unless ARCHIVED)
    # ------------------------------------------------------------------

    def add_additional_service(
        self,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        now: datetime,
        description: ServiceDescription | None = None,
        enabled: bool = True,
    ) -> list[DomainEvent]:
        """Add an optional paid service (fixed price, not per participant)."""
        self._ensure_not_archived()
        service = AdditionalService.create(service_id=service_id, name=name, price=price, description=description, enabled=enabled)
        self._additional_services[service_id] = service
        self._touch(now)
        return [
            AdditionalServiceAdded(
                aggregate_id=self._id.value,
                service_id=service_id,
                name=name,
                amount=str(price.amount),
                currency=price.currency,
                enabled=enabled,
            )
        ]

    def update_additional_service(
        self,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        description: ServiceDescription | None,
        now: datetime,
    ) -> None:
        self._ensure_not_archived()
        self._require_service(service_id).update(name=name, price=price, description=description)
        self._touch(now)

    def enable_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_service(service_id).enable()
        self._touch(now)

    def disable_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_service(service_id).disable()
        self._touch(now)

    def remove_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_service(service_id)
        del self._additional_services[service_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Settings (behaviour flags; allowed unless ARCHIVED)
    # ------------------------------------------------------------------

    def update_settings(self, *, settings: CompetitionSettings, now: datetime) -> list[DomainEvent]:
        """Replace the competition's behaviour settings wholesale."""
        self._ensure_not_archived()
        self._settings = settings
        self._touch(now)
        return [CompetitionSettingsChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Registration deadlines (allowed unless ARCHIVED)
    # ------------------------------------------------------------------

    def update_deadlines(self, *, deadlines: RegistrationDeadlines, now: datetime) -> list[DomainEvent]:
        """Replace the registration deadlines (the VO enforces non-contradiction)."""
        self._ensure_not_archived()
        self._deadlines = deadlines
        self._touch(now)
        return [CompetitionDeadlineChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Branding (allowed unless ARCHIVED)
    # ------------------------------------------------------------------

    def update_branding(
        self,
        *,
        logo: FileReference | None = None,
        banner: FileReference | None = None,
        poster: FileReference | None = None,
        now: datetime,
    ) -> list[DomainEvent]:
        """Replace the competition's branding assets (logo, banner, poster)."""
        self._ensure_not_archived()
        self._branding = CompetitionBranding(logo=logo, banner=banner, poster=poster)
        self._touch(now)
        return [CompetitionBrandingChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Contacts (allowed unless ARCHIVED; exactly one primary)
    # ------------------------------------------------------------------

    def add_contact(
        self,
        *,
        contact_id: ContactId,
        contact_type: ContactType,
        value: ContactValue,
        now: datetime,
        is_primary: bool = False,
    ) -> list[DomainEvent]:
        """Add an official contact.

        Rejects duplicates (same type + value). The first contact added always
        becomes primary; passing ``is_primary`` (or being first) makes this the
        sole primary, demoting any previous one.
        """
        self._ensure_not_archived()
        if any(c.type is contact_type and c.value == value for c in self._contacts.values()):
            raise DuplicateContactError(f"A {contact_type.value} contact with this value already exists.")
        make_primary = is_primary or not self._contacts
        contact = Contact.create(contact_id=contact_id, contact_type=contact_type, value=value, is_primary=make_primary)
        if make_primary:
            self._demote_other_primaries(contact_id)
        self._contacts[contact_id] = contact
        self._touch(now)
        return [
            CompetitionContactAdded(
                aggregate_id=self._id.value,
                contact_id=contact_id,
                contact_type=contact_type,
                value=value,
                is_primary=make_primary,
            )
        ]

    def set_primary_contact(self, *, contact_id: ContactId, now: datetime) -> None:
        """Make ``contact_id`` the sole primary contact."""
        self._ensure_not_archived()
        contact = self._require_contact(contact_id)
        if contact.is_primary:
            return
        self._demote_other_primaries(contact_id)
        contact.mark_primary()
        self._touch(now)

    def remove_contact(self, *, contact_id: ContactId, now: datetime) -> list[DomainEvent]:
        """Remove a contact. If it was primary, promote another (if any remain)."""
        self._ensure_not_archived()
        contact = self._require_contact(contact_id)
        was_primary = contact.is_primary
        del self._contacts[contact_id]
        if was_primary:
            remaining = next(iter(self._contacts.values()), None)
            if remaining is not None:
                remaining.mark_primary()
        self._touch(now)
        return [CompetitionContactRemoved(aggregate_id=self._id.value, contact_id=contact_id)]

    def _demote_other_primaries(self, keep: ContactId) -> None:
        for cid, existing in self._contacts.items():
            if cid != keep and existing.is_primary:
                existing.unmark_primary()

    # ------------------------------------------------------------------
    # Public information blocks (allowed unless ARCHIVED)
    # ------------------------------------------------------------------

    def add_information_block(
        self,
        *,
        block_id: InformationBlockId,
        title: InformationBlockTitle,
        content: RichText,
        now: datetime,
        published: bool = False,
        sort_order: int = 0,
    ) -> InformationBlock:
        """Add a public-information block. Titles are unique within the competition."""
        self._ensure_not_archived()
        if any(b.title == title for b in self._information_blocks.values()):
            raise DuplicateInformationBlockError(f"An information block titled {title.value!r} already exists.")
        block = InformationBlock.create(block_id=block_id, title=title, content=content, published=published, sort_order=sort_order)
        self._information_blocks[block_id] = block
        self._touch(now)
        return block

    def update_information_block(
        self,
        *,
        block_id: InformationBlockId,
        title: InformationBlockTitle,
        content: RichText,
        sort_order: int,
        now: datetime,
    ) -> None:
        self._ensure_not_archived()
        block = self._require_information_block(block_id)
        if any(bid != block_id and b.title == title for bid, b in self._information_blocks.items()):
            raise DuplicateInformationBlockError(f"An information block titled {title.value!r} already exists.")
        block.edit(title=title, content=content, sort_order=sort_order)
        self._touch(now)

    def publish_information_block(self, *, block_id: InformationBlockId, now: datetime) -> list[DomainEvent]:
        self._ensure_not_archived()
        block = self._require_information_block(block_id)
        if block.is_published:
            return []
        block.publish()
        self._touch(now)
        return [CompetitionInformationPublished(aggregate_id=self._id.value, block_id=block_id, title=block.title)]

    def hide_information_block(self, *, block_id: InformationBlockId, now: datetime) -> list[DomainEvent]:
        self._ensure_not_archived()
        block = self._require_information_block(block_id)
        if not block.is_published:
            return []
        block.hide()
        self._touch(now)
        return [CompetitionInformationHidden(aggregate_id=self._id.value, block_id=block_id)]

    def remove_information_block(self, *, block_id: InformationBlockId, now: datetime) -> None:
        self._ensure_not_archived()
        self._require_information_block(block_id)
        del self._information_blocks[block_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def publication_report(self) -> CompetitionPublicationReport:
        """A structured verdict on whether the competition can be published.

        ``errors`` block publication; ``warnings`` are advisory. Callers use this to
        show the organizer exactly what is missing (see :class:`CompetitionPublicationReport`).
        """
        errors: list[PublicationIssue] = []
        warnings: list[PublicationIssue] = []
        if not self._categories:
            errors.append(PublicationIssue(PublicationIssueCode.NO_CATEGORIES, "At least one category is required."))
        if not self._disciplines:
            errors.append(PublicationIssue(PublicationIssueCode.NO_DISCIPLINES, "At least one discipline is required."))
        if not self._age_categories:
            errors.append(PublicationIssue(PublicationIssueCode.NO_AGE_CATEGORIES, "At least one age category is required."))
        if not self._participant_groups:
            errors.append(PublicationIssue(PublicationIssueCode.NO_PARTICIPANT_GROUPS, "At least one participant group is required."))
        if not self._formats:
            errors.append(PublicationIssue(PublicationIssueCode.NO_PARTICIPATION_FORMATS, "At least one participation format must be enabled."))
        if not self._admission_rules:
            errors.append(PublicationIssue(PublicationIssueCode.NO_ADMISSION_RULES, "At least one admission rule is required."))
        unpriced = sum(1 for combination in self._admission_rules if combination not in self._pricing_rules)
        if unpriced:
            errors.append(PublicationIssue(PublicationIssueCode.MISSING_PRICING_RULES, f"{unpriced} admissible combination(s) have no price."))
        if self._current_regulation_id is None:
            errors.append(PublicationIssue(PublicationIssueCode.MISSING_REGULATION, "A published regulation is required."))
        used_formats = {combination.participation_format for combination in self._admission_rules}
        for unused in self._formats - used_formats:
            warnings.append(
                PublicationIssue(
                    PublicationIssueCode.UNUSED_PARTICIPATION_FORMAT,
                    f"Format {unused.value} is enabled but unused by any admission rule.",
                )
            )
        return CompetitionPublicationReport(errors=tuple(errors), warnings=tuple(warnings))

    def mark_configured(self, *, now: datetime) -> list[DomainEvent]:
        """Signal that configuration is complete (``DRAFT → CONFIGURED``). Still editable."""
        self._transition_to(CompetitionStatus.CONFIGURED, now=now)
        return []

    def revert_to_draft(self, *, now: datetime) -> list[DomainEvent]:
        """Reopen a configured competition for free editing (``CONFIGURED → DRAFT``)."""
        self._transition_to(CompetitionStatus.DRAFT, now=now)
        return []

    def mark_ready(self, *, now: datetime) -> list[DomainEvent]:
        """Validate the configuration and freeze it (``CONFIGURED → READY``).

        Refuses if the :meth:`publication_report` has blocking errors.
        """
        report = self.publication_report()
        if not report.is_publishable:
            raise PublicationRequirementsNotMetError(report.error_summary())
        self._transition_to(CompetitionStatus.READY, now=now)
        return []

    def revert_to_configured(self, *, now: datetime) -> list[DomainEvent]:
        """Unfreeze a ready competition to edit configuration again (``READY → CONFIGURED``)."""
        self._transition_to(CompetitionStatus.CONFIGURED, now=now)
        return []

    def publish(self, *, now: datetime) -> list[DomainEvent]:
        """Open the competition to applicants (``READY → PUBLISHED``).

        Re-checks the publication report defensively; a READY competition is always
        publishable because its configuration was validated and then frozen.
        """
        report = self.publication_report()
        if not report.is_publishable:
            raise PublicationRequirementsNotMetError(report.error_summary())
        previous = self._status
        self._transition_to(CompetitionStatus.PUBLISHED, now=now)
        return [CompetitionPublished(aggregate_id=self._id.value, previous_status=previous)]

    def open_registration(self, *, now: datetime) -> list[DomainEvent]:
        """Open registration (``PUBLISHED → REGISTRATION_OPEN``)."""
        self._transition_to(CompetitionStatus.REGISTRATION_OPEN, now=now)
        return [CompetitionRegistrationOpened(aggregate_id=self._id.value)]

    def close_registration(self, *, now: datetime) -> list[DomainEvent]:
        """Close registration (``REGISTRATION_OPEN → REGISTRATION_CLOSED``)."""
        self._transition_to(CompetitionStatus.REGISTRATION_CLOSED, now=now)
        return [CompetitionRegistrationClosed(aggregate_id=self._id.value)]

    def start(self, *, now: datetime) -> list[DomainEvent]:
        """Begin running the competition (``REGISTRATION_CLOSED → RUNNING``)."""
        self._transition_to(CompetitionStatus.RUNNING, now=now)
        return [CompetitionStarted(aggregate_id=self._id.value)]

    def complete(self, *, now: datetime) -> list[DomainEvent]:
        """Finish the competition (``RUNNING → COMPLETED``)."""
        self._transition_to(CompetitionStatus.COMPLETED, now=now)
        return [CompetitionCompleted(aggregate_id=self._id.value)]

    def archive(self, *, now: datetime) -> list[DomainEvent]:
        """Retire the competition (any non-archived status → ``ARCHIVED``). It becomes read-only."""
        if self._status is CompetitionStatus.ARCHIVED:
            raise CompetitionAlreadyArchivedError("The competition is already archived.")
        previous = self._status
        self._transition_to(CompetitionStatus.ARCHIVED, now=now)
        return [CompetitionArchived(aggregate_id=self._id.value, previous_status=previous)]

    # ------------------------------------------------------------------
    # Internal invariants & helpers
    # ------------------------------------------------------------------

    def _ensure_not_archived(self) -> None:
        if self._status is CompetitionStatus.ARCHIVED:
            raise CompetitionAlreadyArchivedError("An archived competition is read-only.")

    def _ensure_configurable(self) -> None:
        """Admissibility configuration may change only while DRAFT or CONFIGURED."""
        if self._status not in _CONFIGURABLE_STATUSES:
            raise ConfigurationLockedError(
                f"Competition configuration can only be changed while DRAFT or CONFIGURED, not while {self._status.value}."
            )

    def _require_service(self, service_id: ServiceId) -> AdditionalService:
        service = self._additional_services.get(service_id)
        if service is None:
            raise ServiceNotFoundError(f"No additional service {service_id} in this competition.")
        return service

    def _require_contact(self, contact_id: ContactId) -> Contact:
        contact = self._contacts.get(contact_id)
        if contact is None:
            raise ContactNotFoundError(f"No contact {contact_id} in this competition.")
        return contact

    def _require_information_block(self, block_id: InformationBlockId) -> InformationBlock:
        block = self._information_blocks.get(block_id)
        if block is None:
            raise InformationBlockNotFoundError(f"No information block {block_id} in this competition.")
        return block

    def _transition_to(self, target: CompetitionStatus, *, now: datetime) -> None:
        """Move to ``target`` if the transition is legal from the current status."""
        if target not in _LEGAL_TRANSITIONS[self._status]:
            raise IllegalStatusTransitionError(f"Cannot transition from {self._status.value} to {target.value}.")
        self._status = target
        self._touch(now)

    def _pricing_added_event(self, combination: AdmissionCombination, price: Money) -> PricingRuleAdded:
        return PricingRuleAdded(
            aggregate_id=self._id.value,
            category_id=combination.category_id,
            discipline_id=combination.discipline_id,
            age_category_id=combination.age_category_id,
            participant_group_id=combination.participant_group_id,
            participation_format=combination.participation_format,
            amount=str(price.amount),
            currency=price.currency,
        )

    def _require_category(self, category_id: CategoryId) -> Category:
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError(f"No category {category_id} in this competition.")
        return category

    def _require_discipline(self, discipline_id: DisciplineId) -> Discipline:
        discipline = self._disciplines.get(discipline_id)
        if discipline is None:
            raise DisciplineNotFoundError(f"No discipline {discipline_id} in this competition.")
        return discipline

    def _require_age_category(self, age_category_id: AgeCategoryId) -> AgeCategory:
        age_category = self._age_categories.get(age_category_id)
        if age_category is None:
            raise AgeCategoryNotFoundError(f"No age category {age_category_id} in this competition.")
        return age_category

    def _require_participant_group(self, participant_group_id: ParticipantGroupId) -> ParticipantGroup:
        group = self._participant_groups.get(participant_group_id)
        if group is None:
            raise ParticipantGroupNotFoundError(f"No participant group {participant_group_id} in this competition.")
        return group

    def _require_document(self, document_id: DocumentId) -> CompetitionDocument:
        document = self._documents.get(document_id)
        if document is None:
            raise DocumentNotFoundError(f"No document {document_id} in this competition.")
        return document

    def _validate_combination(self, combination: AdmissionCombination) -> None:
        """Assert every element a rule references exists in this competition and is consistent."""
        ensure_admission_combination_valid(
            combination,
            categories=self._categories,
            disciplines=self._disciplines,
            age_categories=self._age_categories,
            participant_groups=self._participant_groups,
            formats=self._formats,
        )

    def _next_category_sort_order(self) -> int:
        if not self._categories:
            return 0
        return max(c.sort_order for c in self._categories.values()) + 1

    def _next_age_category_sort_order(self, category_id: CategoryId) -> int:
        siblings = [a for a in self._age_categories.values() if a.category_id == category_id]
        if not siblings:
            return 0
        return max(a.sort_order for a in siblings) + 1

    def _next_participant_group_sort_order(self, category_id: CategoryId) -> int:
        siblings = [g for g in self._participant_groups.values() if g.category_id == category_id]
        if not siblings:
            return 0
        return max(g.sort_order for g in siblings) + 1

    def _next_discipline_sort_order(self, category_id: CategoryId) -> int:
        siblings = [d for d in self._disciplines.values() if d.category_id == category_id]
        if not siblings:
            return 0
        return max(d.sort_order for d in siblings) + 1

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Competition) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Competition(id={self._id!r}, title={self._title.value!r}, season={self._season.value!r}, status={self._status})"
