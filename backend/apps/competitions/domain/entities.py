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
* *Online streaming* — a streaming child entity holding stream references,
  optionally linked to a participation format by id.
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
from enum import Enum
from typing import TYPE_CHECKING, Final

from .contacts_configuration import ContactsConfiguration
from .events import (
    AdditionalServiceAdded,
    AdmissionRuleAdded,
    AdmissionRuleRemoved,
    CompetitionBrandingChanged,
    CompetitionCompleted,
    CompetitionContactAdded,
    CompetitionContactRemoved,
    CompetitionContactsConfigChanged,
    CompetitionCreated,
    CompetitionDeadlineChanged,
    CompetitionGeneralInformationUpdated,
    CompetitionInformationHidden,
    CompetitionInformationPublished,
    CompetitionLandingConfigurationChanged,
    CompetitionPublished,
    CompetitionSettingsChanged,
    CompetitionStarted,
    DomainEvent,
    NominationRegistrationResumed,
    NominationRegistrationScheduled,
    NominationRegistrationStopped,
    ParticipationFormatDisabled,
    ParticipationFormatEnabled,
    PricingRuleAdded,
    PricingRuleRemoved,
    RegulationPublished,
)
from .exceptions import (
    AdmissionRuleInUseError,
    AdmissionRuleNotFoundError,
    AgeCategoryGroupMismatchError,
    AgeCategoryInUseError,
    AgeCategoryNotFoundError,
    CategoryInUseError,
    CategoryNotFoundError,
    CompetitionAlreadyCompletedError,
    ConfigurationLockedError,
    ContactNotFoundError,
    DirectConstructionError,
    DisciplineCategoryMismatchError,
    DisciplineInUseError,
    DisciplineNotFoundError,
    DocumentNotFoundError,
    DuplicateAdmissionRuleError,
    DuplicateAgeCategoryNameError,
    DuplicateCategoryError,
    DuplicateContactError,
    DuplicateDisciplineError,
    DuplicateInformationBlockError,
    DuplicateParticipantGroupError,
    DuplicateParticipationFormatError,
    DuplicatePricingRuleError,
    EmptyAdditionalServiceFormatsError,
    IllegalStatusTransitionError,
    InformationBlockNotFoundError,
    InvalidMoneyError,
    InvalidSortOrderError,
    OverlappingAgeRangeError,
    ParticipantGroupInUseError,
    ParticipantGroupNotFoundError,
    ParticipationFormatInUseError,
    ParticipationFormatNotEnabledError,
    ParticipationFormatNotFoundError,
    PricingRuleNotFoundError,
    PublicationRequirementsNotMetError,
    RegulationNotFoundError,
    ServiceNotFoundError,
)
from .landing_configuration import LandingConfiguration
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
    ParticipationFormatDescription,
    ParticipationFormatId,
    ParticipationFormatName,
    PricingCalculationType,
    PricingRule,
    PublicationIssue,
    PublicationIssueCode,
    RegistrationDeadlines,
    RegistrationWindow,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    Season,
    ServiceBillingModel,
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


class _Unset(Enum):
    """The type of the "argument not supplied" sentinel.

    A single-member ``Enum`` rather than a bare ``object()``. The checker narrows enum
    members as literals, so ``if x is not _SENTINEL:`` genuinely removes the sentinel
    from the union inside the branch — which is the entire point of having one. A bare
    ``object()`` can only be typed as ``object``, so it fitted no parameter's
    annotation and every partial-update signature below was an error.
    """

    TOKEN = "UNSET"


#: Sentinel for distinguishing "not supplied" from ``None`` in partial updates.
_SENTINEL: Final = _Unset.TOKEN

#: The lifecycle transitions the aggregate permits. ``COMPLETED`` is terminal.
#: Registration is scheduled per nomination, so there is no competition-wide
#: registration-open/closed state: a ``PUBLISHED`` competition goes straight to
#: ``RUNNING`` while its nominations open and close on their own windows.
_LEGAL_TRANSITIONS: Final[dict[CompetitionStatus, frozenset[CompetitionStatus]]] = {
    CompetitionStatus.DRAFT: frozenset({CompetitionStatus.CONFIGURED}),
    CompetitionStatus.CONFIGURED: frozenset({CompetitionStatus.DRAFT, CompetitionStatus.READY}),
    CompetitionStatus.READY: frozenset({CompetitionStatus.CONFIGURED, CompetitionStatus.PUBLISHED}),
    CompetitionStatus.PUBLISHED: frozenset({CompetitionStatus.RUNNING}),
    CompetitionStatus.RUNNING: frozenset({CompetitionStatus.COMPLETED}),
    CompetitionStatus.COMPLETED: frozenset(),
}

#: Statuses in which the admissibility configuration (taxonomy, formats, admission
#: and pricing rules) may still be mutated. Beyond these it is frozen.
_CONFIGURABLE_STATUSES: Final = frozenset({CompetitionStatus.DRAFT, CompetitionStatus.CONFIGURED})

#: Statuses in which the competition accepts applications (subject to each nomination's
#: own registration window). Registration is per-nomination, gated by these statuses.
_SUBMISSION_STATUSES: Final = frozenset({CompetitionStatus.PUBLISHED, CompetitionStatus.RUNNING})


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
    formats: Mapping[ParticipationFormatId, ParticipationFormat],
) -> None:
    """Assert every element ``combination`` references exists and is mutually consistent."""
    if combination.category_id not in categories:
        raise CategoryNotFoundError(f"No category {combination.category_id} in this configuration.")
    discipline = disciplines.get(combination.discipline_id)
    if discipline is None:
        raise DisciplineNotFoundError(f"No discipline {combination.discipline_id} in this configuration.")
    if discipline.category_id != combination.category_id:
        raise DisciplineCategoryMismatchError("The discipline does not belong to the stated category.")
    group = participant_groups.get(combination.participant_group_id)
    if group is None:
        raise ParticipantGroupNotFoundError(f"No participant group {combination.participant_group_id} in this configuration.")
    age_category = age_categories.get(combination.age_category_id)
    if age_category is None:
        raise AgeCategoryNotFoundError(f"No age category {combination.age_category_id} in this configuration.")
    if age_category.participant_group_id != combination.participant_group_id:
        raise AgeCategoryGroupMismatchError("The age category does not belong to the stated participant group.")
    participation_format = formats.get(combination.participation_format_id)
    if participation_format is None:
        raise ParticipationFormatNotFoundError(f"No participation format {combination.participation_format_id} in this configuration.")
    if not participation_format.enabled:
        raise ParticipationFormatNotEnabledError(f"Participation format {combination.participation_format_id} is not enabled.")


def ensure_age_range_free(
    age_categories: Mapping[AgeCategoryId, AgeCategory],
    age_range: AgeRange,
    *,
    participant_group_id: ParticipantGroupId,
    exclude: AgeCategoryId | None = None,
) -> None:
    """Assert ``age_range`` does not overlap any existing age category within the same participant group."""
    for aid, existing in age_categories.items():
        if aid == exclude:
            continue
        if existing.participant_group_id != participant_group_id:
            continue
        if existing.age_range.overlaps(age_range):
            raise OverlappingAgeRangeError(f"Age range {age_range} overlaps existing range {existing.age_range}.")


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
    """A competition category (a *nomination*) — the top of the taxonomy (e.g. Vocal, Choreography).

    A nomination owns its own registration schedule: a :class:`~apps.competitions.
    domain.value_objects.RegistrationWindow` (open/close instants) plus an early-stop
    flag. Registration is decided per nomination — the competition has no single
    application deadline — so each nomination opens, closes on time, or is stopped
    early independently of the others.
    """

    _id: CategoryId
    _name: CategoryName
    _description: CategoryDescription | None = None
    _sort_order: int = 0
    _registration: RegistrationWindow = field(default_factory=RegistrationWindow)
    _registration_stopped: bool = False

    @classmethod
    def create(
        cls,
        *,
        category_id: CategoryId,
        name: CategoryName,
        description: CategoryDescription | None = None,
        sort_order: int = 0,
        registration: RegistrationWindow | None = None,
        registration_stopped: bool = False,
    ) -> Category:
        return cls(
            _id=category_id,
            _name=name,
            _description=description,
            _sort_order=_validate_sort_order(sort_order),
            _registration=registration if registration is not None else RegistrationWindow(),
            _registration_stopped=registration_stopped,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        category_id: CategoryId,
        name: CategoryName,
        description: CategoryDescription | None = None,
        sort_order: int = 0,
        registration: RegistrationWindow | None = None,
        registration_stopped: bool = False,
    ) -> Category:
        return cls(
            _id=category_id,
            _name=name,
            _description=description,
            _sort_order=sort_order,
            _registration=registration if registration is not None else RegistrationWindow(),
            _registration_stopped=registration_stopped,
        )

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

    @property
    def registration(self) -> RegistrationWindow:
        return self._registration

    @property
    def is_registration_stopped(self) -> bool:
        return self._registration_stopped

    def schedule_registration(self, window: RegistrationWindow) -> None:
        """Set (or replace) this nomination's registration window."""
        self._registration = window

    def stop_registration(self) -> None:
        """Stop this nomination's registration early (closed regardless of the window)."""
        self._registration_stopped = True

    def resume_registration(self) -> None:
        """Lift an early stop; the window's instants govern openness again."""
        self._registration_stopped = False

    def accepts_submissions(self, now: datetime) -> bool:
        """Whether this nomination accepts applications at ``now``.

        Open only when not stopped early **and** the configured window admits
        ``now``; an unscheduled nomination is closed.
        """
        return not self._registration_stopped and self._registration.is_open(now)

    def rename(self, name: CategoryName) -> None:
        self._name = name

    def update(
        self,
        *,
        name: CategoryName | None = None,
        description: CategoryDescription | None | _Unset = _SENTINEL,
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
    """An age band configured for this competition, scoped to a participant group (solo/duet/…)."""

    _id: AgeCategoryId
    _participant_group_id: ParticipantGroupId
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
        participant_group_id: ParticipantGroupId,
        name: AgeCategoryName,
        age_range: AgeRange,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int = 0,
    ) -> AgeCategory:
        _validate_type_method_consistency(age_category_type, mixed_calculation_method)
        return cls(
            _id=age_category_id,
            _participant_group_id=participant_group_id,
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
        participant_group_id: ParticipantGroupId,
        name: AgeCategoryName,
        age_range: AgeRange,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int = 0,
    ) -> AgeCategory:
        return cls(
            _id=age_category_id,
            _participant_group_id=participant_group_id,
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
    def participant_group_id(self) -> ParticipantGroupId:
        return self._participant_group_id

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
        mixed_calculation_method: MixedAgeCalculationMethod | None | _Unset = _SENTINEL,
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
        return (
            f"AgeCategory(id={self._id!r}, participant_group_id={self._participant_group_id!r}, name={self._name.value!r}, range={self._age_range})"
        )


@dataclass(slots=True, eq=False, repr=False)
class ParticipantGroup:
    """A participant grouping mapped from a headcount band, configured per competition.

    Groups are competition-wide (Solo=1, Duet=2, Ensemble=3-5, Choir=6+; …) — each
    headcount maps to exactly one group, shared across all nominations. Age bands are
    scoped to a group, not to a nomination.
    """

    _id: ParticipantGroupId
    _name: ParticipantGroupName
    _count_range: ParticipantCountRange
    _description: ParticipantGroupDescription | None = None
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        participant_group_id: ParticipantGroupId,
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        description: ParticipantGroupDescription | None = None,
        sort_order: int = 0,
    ) -> ParticipantGroup:
        return cls(
            _id=participant_group_id,
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
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        description: ParticipantGroupDescription | None = None,
        sort_order: int = 0,
    ) -> ParticipantGroup:
        return cls(
            _id=participant_group_id,
            _name=name,
            _count_range=count_range,
            _description=description,
            _sort_order=sort_order,
        )

    @property
    def id(self) -> ParticipantGroupId:
        return self._id

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
        description: ParticipantGroupDescription | None | _Unset = _SENTINEL,
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
class ParticipationFormat:
    """A named mode of participation for a competition (e.g. offline / online).

    Organizers configure formats as data — name, optional description, enabled
    flag and sort order — rather than toggling a fixed enumeration. Soft-disable
    (``enabled=False``) keeps the format in the graph so admission/pricing rules
    that reference it remain valid; hard removal is refused while referenced.
    """

    _id: ParticipationFormatId
    _name: ParticipationFormatName
    _description: ParticipationFormatDescription | None = None
    _enabled: bool = True
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        format_id: ParticipationFormatId,
        name: ParticipationFormatName,
        description: ParticipationFormatDescription | None = None,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> ParticipationFormat:
        return cls(
            _id=format_id,
            _name=name,
            _description=description,
            _enabled=enabled,
            _sort_order=_validate_sort_order(sort_order),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        format_id: ParticipationFormatId,
        name: ParticipationFormatName,
        description: ParticipationFormatDescription | None = None,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> ParticipationFormat:
        return cls(
            _id=format_id,
            _name=name,
            _description=description,
            _enabled=enabled,
            _sort_order=sort_order,
        )

    @property
    def id(self) -> ParticipationFormatId:
        return self._id

    @property
    def name(self) -> ParticipationFormatName:
        return self._name

    @property
    def description(self) -> ParticipationFormatDescription | None:
        return self._description

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def update(
        self,
        *,
        name: ParticipationFormatName | None = None,
        description: ParticipationFormatDescription | None | _Unset = _SENTINEL,
        enabled: bool | None = None,
        sort_order: int | None = None,
    ) -> None:
        if name is not None:
            self._name = name
        if description is not _SENTINEL:
            self._description = description
        if enabled is not None:
            self._enabled = enabled
        if sort_order is not None:
            self._sort_order = _validate_sort_order(sort_order)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ParticipationFormat) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ParticipationFormat(id={self._id!r}, name={self._name.value!r}, enabled={self._enabled})"


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
    """An optional paid service scoped to selected participation formats.

    Examples: medal (in-person only), shipping / e-diploma (online only), video
    recording (in-person only). Availability is a multi-select of existing
    :class:`ParticipationFormat` ids — never a hardcoded offline/online flag.

    ``billing_model`` decides how ``price`` becomes a line total:
    per participant (× headcount) or per performance (fixed).
    """

    _id: ServiceId
    _name: ServiceName
    _price: Money
    _billing_model: ServiceBillingModel
    _available_format_ids: frozenset[ParticipationFormatId]
    _description: ServiceDescription | None = None
    _required: bool = False
    _enabled: bool = True
    _sort_order: int = 0

    @classmethod
    def create(
        cls,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        available_format_ids: Iterable[ParticipationFormatId],
        billing_model: ServiceBillingModel = ServiceBillingModel.PER_PARTICIPANT,
        description: ServiceDescription | None = None,
        required: bool = False,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> AdditionalService:
        formats = frozenset(available_format_ids)
        if not formats:
            raise EmptyAdditionalServiceFormatsError("An additional service must be available for at least one participation format.")
        return cls(
            _id=service_id,
            _name=name,
            _price=price,
            _billing_model=billing_model,
            _available_format_ids=formats,
            _description=description,
            _required=required,
            _enabled=enabled,
            _sort_order=_validate_sort_order(sort_order),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        available_format_ids: Iterable[ParticipationFormatId],
        billing_model: ServiceBillingModel = ServiceBillingModel.PER_PARTICIPANT,
        description: ServiceDescription | None = None,
        required: bool = False,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> AdditionalService:
        return cls(
            _id=service_id,
            _name=name,
            _price=price,
            _billing_model=billing_model,
            _available_format_ids=frozenset(available_format_ids),
            _description=description,
            _required=required,
            _enabled=enabled,
            _sort_order=sort_order,
        )

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
    def billing_model(self) -> ServiceBillingModel:
        return self._billing_model

    @property
    def available_format_ids(self) -> frozenset[ParticipationFormatId]:
        return self._available_format_ids

    @property
    def description(self) -> ServiceDescription | None:
        return self._description

    @property
    def required(self) -> bool:
        return self._required

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def sort_order(self) -> int:
        return self._sort_order

    def is_available_for(self, format_id: ParticipationFormatId) -> bool:
        return format_id in self._available_format_ids

    def total_for(self, participant_count: int) -> Money:
        """Line total for ``participant_count`` under this service's billing model."""
        if participant_count < 1:
            raise InvalidMoneyError("Participant count must be at least 1 to compute a total.")
        if self._billing_model is ServiceBillingModel.PER_PERFORMANCE:
            return self._price
        return Money(amount=self._price.amount * participant_count, currency=self._price.currency)

    def update(
        self,
        *,
        name: ServiceName,
        price: Money,
        description: ServiceDescription | None,
        available_format_ids: Iterable[ParticipationFormatId],
        billing_model: ServiceBillingModel,
        required: bool,
        sort_order: int,
    ) -> None:
        formats = frozenset(available_format_ids)
        if not formats:
            raise EmptyAdditionalServiceFormatsError("An additional service must be available for at least one participation format.")
        self._name = name
        self._price = price
        self._description = description
        self._available_format_ids = formats
        self._billing_model = billing_model
        self._required = required
        self._sort_order = _validate_sort_order(sort_order)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AdditionalService) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"AdditionalService(id={self._id!r}, name={self._name.value!r}, billing={self._billing_model.value}, enabled={self._enabled})"


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

    Guards its full lifecycle (``DRAFT → CONFIGURED → READY → PUBLISHED → RUNNING →
    COMPLETED``; registration is scheduled per nomination, not as a competition-wide
    state) and every cross-element invariant of its configuration. Equality/hashing
    is by :class:`CompetitionId`.
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
    _contacts_config: ContactsConfiguration = field(default_factory=ContactsConfiguration.default)
    _landing_config: LandingConfiguration = field(default_factory=LandingConfiguration.default)
    _categories: dict[CategoryId, Category] = field(default_factory=dict)
    _disciplines: dict[DisciplineId, Discipline] = field(default_factory=dict)
    _age_categories: dict[AgeCategoryId, AgeCategory] = field(default_factory=dict)
    _participant_groups: dict[ParticipantGroupId, ParticipantGroup] = field(default_factory=dict)
    _formats: dict[ParticipationFormatId, ParticipationFormat] = field(default_factory=dict)
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
        contacts_config: ContactsConfiguration | None = None,
        landing_config: LandingConfiguration | None = None,
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
            _contacts_config=contacts_config if contacts_config is not None else ContactsConfiguration.default(),
            _landing_config=landing_config if landing_config is not None else LandingConfiguration.default(),
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
        contacts_config: ContactsConfiguration | None = None,
        landing_config: LandingConfiguration | None = None,
        deadlines: RegistrationDeadlines | None = None,
        categories: Sequence[Category] = (),
        disciplines: Sequence[Discipline] = (),
        age_categories: Sequence[AgeCategory] = (),
        participant_groups: Sequence[ParticipantGroup] = (),
        formats: Sequence[ParticipationFormat] = (),
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
            _contacts_config=contacts_config if contacts_config is not None else ContactsConfiguration.default(),
            _landing_config=landing_config if landing_config is not None else LandingConfiguration.default(),
            _deadlines=deadlines if deadlines is not None else RegistrationDeadlines(),
            _categories={c.id: c for c in categories},
            _disciplines={d.id: d for d in disciplines},
            _age_categories={a.id: a for a in age_categories},
            _participant_groups={g.id: g for g in participant_groups},
            _formats={f.id: f for f in formats},
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
        format_map: dict[ParticipationFormatId, ParticipationFormatId] = {}

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
        # Groups must exist before age categories, which are scoped to a group.
        for group in template.participant_groups:
            new_group_id = ParticipantGroupId.generate()
            group_map[group.id] = new_group_id
            self._participant_groups[new_group_id] = ParticipantGroup.create(
                participant_group_id=new_group_id,
                name=group.name,
                count_range=group.count_range,
                description=group.description,
                sort_order=group.sort_order,
            )
        for age_category in template.age_categories:
            new_age_id = AgeCategoryId.generate()
            age_map[age_category.id] = new_age_id
            self._age_categories[new_age_id] = AgeCategory.create(
                age_category_id=new_age_id,
                participant_group_id=group_map[age_category.participant_group_id],
                name=age_category.name,
                age_range=age_category.age_range,
                age_category_type=age_category.type,
                mixed_calculation_method=age_category.mixed_calculation_method,
                sort_order=age_category.sort_order,
            )
        for participation_format in template.participation_formats:
            new_format_id = ParticipationFormatId.generate()
            format_map[participation_format.id] = new_format_id
            self._formats[new_format_id] = ParticipationFormat.create(
                format_id=new_format_id,
                name=participation_format.name,
                description=participation_format.description,
                enabled=participation_format.enabled,
                sort_order=participation_format.sort_order,
            )

        def _remap(combination: AdmissionCombination) -> AdmissionCombination:
            return AdmissionCombination(
                category_id=category_map[combination.category_id],
                discipline_id=discipline_map[combination.discipline_id],
                age_category_id=age_map[combination.age_category_id],
                participant_group_id=group_map[combination.participant_group_id],
                participation_format_id=format_map[combination.participation_format_id],
            )

        for rule in template.admission_rules:
            remapped = _remap(rule.combination)
            self._admission_rules[remapped] = AdmissionRule(combination=remapped)
        for pricing in template.pricing_rules:
            remapped = _remap(pricing.combination)
            self._pricing_rules[remapped] = PricingRule(
                combination=remapped,
                price_per_participant=pricing.price_per_participant,
                calculation_type=pricing.calculation_type,
            )

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
    def contacts_config(self) -> ContactsConfiguration:
        return self._contacts_config

    @property
    def landing_config(self) -> LandingConfiguration:
        return self._landing_config

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
    def participation_formats(self) -> tuple[ParticipationFormat, ...]:
        return tuple(self._formats.values())

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
        return tuple(
            sorted(
                self._additional_services.values(),
                key=lambda s: (s.sort_order, s.name.value, s.id.json()),
            )
        )

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

    def is_completed(self) -> bool:
        return self._status is CompetitionStatus.COMPLETED

    def disciplines_of(self, category_id: CategoryId) -> tuple[Discipline, ...]:
        """All disciplines belonging to ``category_id``."""
        return tuple(d for d in self._disciplines.values() if d.category_id == category_id)

    def age_categories_of(self, participant_group_id: ParticipantGroupId) -> tuple[AgeCategory, ...]:
        """All age categories belonging to ``participant_group_id``."""
        return tuple(a for a in self._age_categories.values() if a.participant_group_id == participant_group_id)

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
        """The unit list price for ``combination``, or ``None`` if unpriced."""
        rule = self._pricing_rules.get(combination)
        return rule.price_per_participant if rule is not None else None

    def pricing_rule_for(self, combination: AdmissionCombination) -> PricingRule | None:
        """The pricing rule for ``combination``, or ``None`` if unpriced."""
        return self._pricing_rules.get(combination)

    def calculate_price_for(self, combination: AdmissionCombination, participant_count: int) -> Money | None:
        """Application total for ``combination`` given ``participant_count``, or ``None`` if unpriced."""
        rule = self._pricing_rules.get(combination)
        if rule is None:
            return None
        return rule.total_for(participant_count)

    # ------------------------------------------------------------------
    # Deadline queries (answer "is X still allowed at `now`?")
    # ------------------------------------------------------------------
    #
    # These answer the *deadline* question only (and refuse everything once the
    # competition is COMPLETED). Layering admission/lifecycle policy on top is the
    # Application context's job; the Competition merely owns the cut-off dates.

    def is_application_allowed(self, now: datetime) -> bool:
        """Whether the competition accepts applications at ``now`` in *any* nomination.

        Registration is scheduled per nomination, so the competition-level answer is
        "is at least one nomination open?" — used at entry points (creating an
        application, adding a submission) before a nomination has been chosen.
        """
        return self.is_any_nomination_open(now)

    def accepts_submissions_for(self, category_id: CategoryId, now: datetime) -> bool:
        """Whether the nomination ``category_id`` accepts applications at ``now``.

        Requires the competition to be PUBLISHED or RUNNING and the nomination's own
        registration window to be open (not stopped early, within its dates). Closed
        otherwise, or when the nomination is unknown.
        """
        if self._status not in _SUBMISSION_STATUSES:
            return False
        category = self._categories.get(category_id)
        return category is not None and category.accepts_submissions(now)

    def is_any_nomination_open(self, now: datetime) -> bool:
        """Whether at least one nomination currently accepts applications at ``now``."""
        return self._status in _SUBMISSION_STATUSES and any(c.accepts_submissions(now) for c in self._categories.values())

    def is_payment_allowed(self, now: datetime) -> bool:
        return not self.is_completed() and self._deadlines.is_open(DeadlineKind.PAYMENT, now)

    def is_music_upload_allowed(self, now: datetime) -> bool:
        return not self.is_completed() and self._deadlines.is_open(DeadlineKind.MUSIC_UPLOAD, now)

    def is_document_upload_allowed(self, now: datetime) -> bool:
        return not self.is_completed() and self._deadlines.is_open(DeadlineKind.DOCUMENT_UPLOAD, now)

    def is_correction_allowed(self, now: datetime) -> bool:
        return not self.is_completed() and self._deadlines.is_open(DeadlineKind.CORRECTION, now)

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
        """Replace the competition's general information (allowed unless COMPLETED).

        General information is presentation, not admissibility configuration, so it
        may be edited even after publication — it cannot invalidate an application.
        """
        self._ensure_not_completed()
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
        description: CategoryDescription | None | _Unset = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        self._ensure_configurable()
        category = self._require_category(category_id)
        if name is not None and any(cid != category_id and c.name == name for cid, c in self._categories.items()):
            raise DuplicateCategoryError(f"A category named {name.value!r} already exists.")
        category.update(name=name, description=description, sort_order=sort_order)
        self._touch(now)

    def remove_category(self, *, category_id: CategoryId, now: datetime) -> None:
        """Remove a category. Refused while any discipline or rule references it."""
        self._ensure_configurable()
        self._require_category(category_id)
        if any(d.category_id == category_id for d in self._disciplines.values()):
            raise CategoryInUseError("The category still has disciplines.")
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
        participant_group_id: ParticipantGroupId,
        name: AgeCategoryName,
        age_range: AgeRange,
        now: datetime,
        age_category_type: AgeCategoryType = AgeCategoryType.STANDARD,
        mixed_calculation_method: MixedAgeCalculationMethod | None = None,
        sort_order: int | None = None,
    ) -> AgeCategory:
        """Add an age band to a participant group. Overlapping ranges are refused within the group."""
        self._ensure_configurable()
        self._require_participant_group(participant_group_id)
        ensure_age_range_free(self._age_categories, age_range, participant_group_id=participant_group_id)
        if any(a.participant_group_id == participant_group_id and a.name == name for a in self._age_categories.values()):
            raise DuplicateAgeCategoryNameError(f"An age category named {name.value!r} already exists in this participant group.")
        if sort_order is None:
            sort_order = self._next_age_category_sort_order(participant_group_id)
        age_category = AgeCategory.create(
            age_category_id=age_category_id,
            participant_group_id=participant_group_id,
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
        mixed_calculation_method: MixedAgeCalculationMethod | None | _Unset = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        """Partial update of an age category (name, age_range, type, method, sort_order)."""
        self._ensure_configurable()
        age_category = self._require_age_category(age_category_id)
        group_id = age_category.participant_group_id
        if name is not None and any(
            aid != age_category_id and a.participant_group_id == group_id and a.name == name for aid, a in self._age_categories.items()
        ):
            raise DuplicateAgeCategoryNameError(f"An age category named {name.value!r} already exists in this participant group.")
        if age_range is not None:
            ensure_age_range_free(self._age_categories, age_range, participant_group_id=group_id, exclude=age_category_id)
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
        name: ParticipantGroupName,
        count_range: ParticipantCountRange,
        now: datetime,
        description: ParticipantGroupDescription | None = None,
        sort_order: int | None = None,
    ) -> ParticipantGroup:
        """Add a competition-wide participant group.

        Names are unique within the competition. Count ranges may overlap: an
        applicant picks the group explicitly, so two groups can share the same
        headcount (e.g. two "Solo" variants) as long as their names differ.
        """
        self._ensure_configurable()
        if any(g.name == name for g in self._participant_groups.values()):
            raise DuplicateParticipantGroupError(f"A participant group named {name.value!r} already exists.")
        if sort_order is None:
            sort_order = self._next_participant_group_sort_order()
        group = ParticipantGroup.create(
            participant_group_id=participant_group_id,
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
        description: ParticipantGroupDescription | None | _Unset = _SENTINEL,
        sort_order: int | None = None,
    ) -> None:
        """Partial update of a participant group (name, range, description, sort_order)."""
        self._ensure_configurable()
        group = self._require_participant_group(participant_group_id)
        if name is not None and any(gid != participant_group_id and g.name == name for gid, g in self._participant_groups.items()):
            raise DuplicateParticipantGroupError(f"A participant group named {name.value!r} already exists.")
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
        if any(a.participant_group_id == participant_group_id for a in self._age_categories.values()):
            raise ParticipantGroupInUseError("The participant group still has age categories.")
        if any(c.participant_group_id == participant_group_id for c in self._admission_rules):
            raise ParticipantGroupInUseError("The participant group is referenced by admission rules.")
        if any(c.participant_group_id == participant_group_id for c in self._pricing_rules):
            raise ParticipantGroupInUseError("The participant group is referenced by pricing rules.")
        del self._participant_groups[participant_group_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Participation formats (DRAFT/CONFIGURED only)
    # ------------------------------------------------------------------

    def add_participation_format(
        self,
        *,
        format_id: ParticipationFormatId,
        name: ParticipationFormatName,
        now: datetime,
        description: ParticipationFormatDescription | None = None,
        enabled: bool = True,
        sort_order: int | None = None,
    ) -> list[DomainEvent]:
        """Add a participation format. Names are unique within the competition."""
        self._ensure_configurable()
        if any(f.name == name for f in self._formats.values()):
            raise DuplicateParticipationFormatError(f"A participation format named {name.value!r} already exists.")
        if sort_order is None:
            sort_order = self._next_format_sort_order()
        self._formats[format_id] = ParticipationFormat.create(
            format_id=format_id,
            name=name,
            description=description,
            enabled=enabled,
            sort_order=sort_order,
        )
        self._touch(now)
        if enabled:
            return [ParticipationFormatEnabled(aggregate_id=self._id.value, participation_format_id=format_id)]
        return []

    def update_participation_format(
        self,
        *,
        format_id: ParticipationFormatId,
        now: datetime,
        name: ParticipationFormatName | None = None,
        description: ParticipationFormatDescription | None | _Unset = _SENTINEL,
        enabled: bool | None = None,
        sort_order: int | None = None,
    ) -> list[DomainEvent]:
        """Partial update of a participation format.

        Soft-disable (``enabled=False``) is always allowed, even when the format
        is referenced by admission or pricing rules.
        """
        self._ensure_configurable()
        participation_format = self._require_participation_format(format_id)
        if name is not None and any(fid != format_id and f.name == name for fid, f in self._formats.items()):
            raise DuplicateParticipationFormatError(f"A participation format named {name.value!r} already exists.")
        was_enabled = participation_format.enabled
        participation_format.update(
            name=name,
            description=description,
            enabled=enabled,
            sort_order=sort_order,
        )
        self._touch(now)
        events: list[DomainEvent] = []
        if enabled is not None and enabled != was_enabled:
            if enabled:
                events.append(ParticipationFormatEnabled(aggregate_id=self._id.value, participation_format_id=format_id))
            else:
                events.append(ParticipationFormatDisabled(aggregate_id=self._id.value, participation_format_id=format_id))
        return events

    def remove_participation_format(self, *, format_id: ParticipationFormatId, now: datetime) -> None:
        """Hard-remove a format. Refused while referenced by admission, pricing, or services."""
        self._ensure_configurable()
        self._require_participation_format(format_id)
        if any(c.participation_format_id == format_id for c in self._admission_rules):
            raise ParticipationFormatInUseError("The format is referenced by admission rules.")
        if any(c.participation_format_id == format_id for c in self._pricing_rules):
            raise ParticipationFormatInUseError("The format is referenced by pricing rules.")
        if any(format_id in s.available_format_ids for s in self._additional_services.values()):
            raise ParticipationFormatInUseError("The format is referenced by additional services.")
        del self._formats[format_id]
        self._settings = self._settings.without_format(format_id)
        self._touch(now)

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
                participation_format_id=combination.participation_format_id,
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
                participation_format_id=combination.participation_format_id,
            )
        ]

    def add_pricing_rule(
        self,
        *,
        combination: AdmissionCombination,
        price_per_participant: Money,
        now: datetime,
        calculation_type: PricingCalculationType = PricingCalculationType.PER_PARTICIPANT,
    ) -> list[DomainEvent]:
        """Set the list price for a combination. Requires an admission rule to exist."""
        self._ensure_configurable()
        self._validate_combination(combination)
        if combination not in self._admission_rules:
            raise AdmissionRuleNotFoundError("Cannot price a combination that is not admissible.")
        if combination in self._pricing_rules:
            raise DuplicatePricingRuleError("A pricing rule for this combination already exists.")
        self._pricing_rules[combination] = PricingRule(
            combination=combination,
            price_per_participant=price_per_participant,
            calculation_type=calculation_type,
        )
        self._touch(now)
        return [self._pricing_added_event(combination, price_per_participant, calculation_type)]

    def change_price(
        self,
        *,
        combination: AdmissionCombination,
        price_per_participant: Money,
        now: datetime,
        calculation_type: PricingCalculationType | None = None,
    ) -> list[DomainEvent]:
        """Change the list price (and optionally calculation type) of an existing pricing rule.

        Emits :class:`~apps.competitions.domain.events.PricingRuleAdded` — the event
        records that a price is now set for the combination, whether first set or changed.
        When ``calculation_type`` is omitted, the existing type is preserved.
        """
        self._ensure_configurable()
        existing = self._pricing_rules.get(combination)
        if existing is None:
            raise PricingRuleNotFoundError("No pricing rule exists for this combination.")
        next_type = calculation_type if calculation_type is not None else existing.calculation_type
        self._pricing_rules[combination] = PricingRule(
            combination=combination,
            price_per_participant=price_per_participant,
            calculation_type=next_type,
        )
        self._touch(now)
        return [self._pricing_added_event(combination, price_per_participant, next_type)]

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
                participation_format_id=combination.participation_format_id,
            )
        ]

    # ------------------------------------------------------------------
    # Regulations (allowed unless COMPLETED — content, not admissibility config)
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
        self._ensure_not_completed()
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
        self._ensure_not_completed()
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
        self._ensure_not_completed()
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
    # Documents (allowed unless COMPLETED — content, not admissibility config)
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
        self._ensure_not_completed()
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
        self._ensure_not_completed()
        document = self._require_document(document_id)
        document.update(title=title, category=category, visibility=visibility, file=file, description=description, sort_order=sort_order)
        self._touch(now)

    def publish_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_document(document_id).publish()
        self._touch(now)

    def unpublish_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_document(document_id).unpublish()
        self._touch(now)

    def remove_document(self, *, document_id: DocumentId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_document(document_id)
        del self._documents[document_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Additional services (optional paid extras; allowed unless COMPLETED)
    # ------------------------------------------------------------------

    def add_additional_service(
        self,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        available_format_ids: Sequence[ParticipationFormatId],
        now: datetime,
        billing_model: ServiceBillingModel = ServiceBillingModel.PER_PARTICIPANT,
        description: ServiceDescription | None = None,
        required: bool = False,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> list[DomainEvent]:
        """Add an optional paid service available for the given participation formats."""
        self._ensure_not_completed()
        for format_id in available_format_ids:
            self._require_participation_format(format_id)
        service = AdditionalService.create(
            service_id=service_id,
            name=name,
            price=price,
            available_format_ids=available_format_ids,
            billing_model=billing_model,
            description=description,
            required=required,
            enabled=enabled,
            sort_order=sort_order,
        )
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
                billing_model=billing_model,
                required=required,
                sort_order=service.sort_order,
            )
        ]

    def update_additional_service(
        self,
        *,
        service_id: ServiceId,
        name: ServiceName,
        price: Money,
        description: ServiceDescription | None,
        available_format_ids: Sequence[ParticipationFormatId],
        billing_model: ServiceBillingModel,
        required: bool,
        sort_order: int,
        now: datetime,
    ) -> None:
        self._ensure_not_completed()
        for format_id in available_format_ids:
            self._require_participation_format(format_id)
        self._require_service(service_id).update(
            name=name,
            price=price,
            description=description,
            available_format_ids=available_format_ids,
            billing_model=billing_model,
            required=required,
            sort_order=sort_order,
        )
        self._touch(now)

    def enable_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_service(service_id).enable()
        self._touch(now)

    def disable_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_service(service_id).disable()
        self._touch(now)

    def remove_additional_service(self, *, service_id: ServiceId, now: datetime) -> None:
        self._ensure_not_completed()
        self._require_service(service_id)
        del self._additional_services[service_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Settings (behaviour flags; allowed unless COMPLETED)
    # ------------------------------------------------------------------

    def update_settings(self, *, settings: CompetitionSettings, now: datetime) -> list[DomainEvent]:
        """Replace the competition's behaviour settings wholesale."""
        self._ensure_not_completed()
        for item in settings.format_requirements:
            self._require_participation_format(item.participation_format_id)
        self._settings = settings
        self._touch(now)
        return [CompetitionSettingsChanged(aggregate_id=self._id.value)]

    def update_contacts_config(self, *, config: ContactsConfiguration, now: datetime) -> list[DomainEvent]:
        """Replace the competition's contacts-module configuration wholesale."""
        self._ensure_not_completed()
        self._contacts_config = config
        self._touch(now)
        return [CompetitionContactsConfigChanged(aggregate_id=self._id.value)]

    def update_landing_config(self, *, config: LandingConfiguration, now: datetime) -> list[DomainEvent]:
        """Replace the competition's public-landing configuration wholesale."""
        self._ensure_not_completed()
        self._landing_config = config
        self._touch(now)
        return [CompetitionLandingConfigurationChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Registration deadlines (allowed unless COMPLETED)
    # ------------------------------------------------------------------

    def update_deadlines(self, *, deadlines: RegistrationDeadlines, now: datetime) -> list[DomainEvent]:
        """Replace the registration deadlines (the VO enforces non-contradiction)."""
        self._ensure_not_completed()
        self._deadlines = deadlines
        self._touch(now)
        return [CompetitionDeadlineChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Branding (allowed unless COMPLETED)
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
        self._ensure_not_completed()
        self._branding = CompetitionBranding(logo=logo, banner=banner, poster=poster)
        self._touch(now)
        return [CompetitionBrandingChanged(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Contacts (allowed unless COMPLETED; exactly one primary)
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
        self._ensure_not_completed()
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
        self._ensure_not_completed()
        contact = self._require_contact(contact_id)
        if contact.is_primary:
            return
        self._demote_other_primaries(contact_id)
        contact.mark_primary()
        self._touch(now)

    def remove_contact(self, *, contact_id: ContactId, now: datetime) -> list[DomainEvent]:
        """Remove a contact. If it was primary, promote another (if any remain)."""
        self._ensure_not_completed()
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
    # Public information blocks (allowed unless COMPLETED)
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
        self._ensure_not_completed()
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
        self._ensure_not_completed()
        block = self._require_information_block(block_id)
        if any(bid != block_id and b.title == title for bid, b in self._information_blocks.items()):
            raise DuplicateInformationBlockError(f"An information block titled {title.value!r} already exists.")
        block.edit(title=title, content=content, sort_order=sort_order)
        self._touch(now)

    def publish_information_block(self, *, block_id: InformationBlockId, now: datetime) -> list[DomainEvent]:
        self._ensure_not_completed()
        block = self._require_information_block(block_id)
        if block.is_published:
            return []
        block.publish()
        self._touch(now)
        return [CompetitionInformationPublished(aggregate_id=self._id.value, block_id=block_id, title=block.title)]

    def hide_information_block(self, *, block_id: InformationBlockId, now: datetime) -> list[DomainEvent]:
        self._ensure_not_completed()
        block = self._require_information_block(block_id)
        if not block.is_published:
            return []
        block.hide()
        self._touch(now)
        return [CompetitionInformationHidden(aggregate_id=self._id.value, block_id=block_id)]

    def remove_information_block(self, *, block_id: InformationBlockId, now: datetime) -> None:
        self._ensure_not_completed()
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
        enabled_formats = [f for f in self._formats.values() if f.enabled]
        if not enabled_formats:
            errors.append(PublicationIssue(PublicationIssueCode.NO_PARTICIPATION_FORMATS, "At least one participation format must be enabled."))
        if not self._admission_rules:
            errors.append(PublicationIssue(PublicationIssueCode.NO_ADMISSION_RULES, "At least one admission rule is required."))
        unpriced = sum(1 for combination in self._admission_rules if combination not in self._pricing_rules)
        if unpriced:
            errors.append(PublicationIssue(PublicationIssueCode.MISSING_PRICING_RULES, f"{unpriced} admissible combination(s) have no price."))
        if self._current_regulation_id is None:
            errors.append(PublicationIssue(PublicationIssueCode.MISSING_REGULATION, "A published regulation is required."))
        used_format_ids = {combination.participation_format_id for combination in self._admission_rules}
        for unused in enabled_formats:
            if unused.id not in used_format_ids:
                warnings.append(
                    PublicationIssue(
                        PublicationIssueCode.UNUSED_PARTICIPATION_FORMAT,
                        f"Format {unused.name.value} is enabled but unused by any admission rule.",
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

    # ------------------------------------------------------------------
    # Per-nomination registration control
    # ------------------------------------------------------------------
    #
    # Registration is scheduled per nomination, not competition-wide. Unlike
    # taxonomy configuration (DRAFT/CONFIGURED only), these are live registration
    # controls: they are allowed at any time until the competition is COMPLETED, so
    # an organizer can set a nomination's window or stop it early after publication.

    def schedule_nomination_registration(
        self,
        *,
        category_id: CategoryId,
        now: datetime,
        opens_at: datetime | None = None,
        closes_at: datetime | None = None,
    ) -> list[DomainEvent]:
        """Set (or replace) a nomination's registration window (open/close instants)."""
        self._ensure_not_completed()
        category = self._require_category(category_id)
        category.schedule_registration(RegistrationWindow(opens_at=opens_at, closes_at=closes_at))
        self._touch(now)
        return [
            NominationRegistrationScheduled(
                aggregate_id=self._id.value,
                category_id=category_id,
                opens_at=opens_at,
                closes_at=closes_at,
            )
        ]

    def stop_nomination_registration(self, *, category_id: CategoryId, now: datetime) -> list[DomainEvent]:
        """Stop a nomination's registration early (closed regardless of its window)."""
        self._ensure_not_completed()
        category = self._require_category(category_id)
        category.stop_registration()
        self._touch(now)
        return [NominationRegistrationStopped(aggregate_id=self._id.value, category_id=category_id)]

    def resume_nomination_registration(self, *, category_id: CategoryId, now: datetime) -> list[DomainEvent]:
        """Lift a nomination's early stop; its window governs openness again."""
        self._ensure_not_completed()
        category = self._require_category(category_id)
        category.resume_registration()
        self._touch(now)
        return [NominationRegistrationResumed(aggregate_id=self._id.value, category_id=category_id)]

    def start(self, *, now: datetime) -> list[DomainEvent]:
        """Begin running the competition (``PUBLISHED → RUNNING``)."""
        self._transition_to(CompetitionStatus.RUNNING, now=now)
        return [CompetitionStarted(aggregate_id=self._id.value)]

    def complete(self, *, now: datetime) -> list[DomainEvent]:
        """Finish the competition (``RUNNING → COMPLETED``). It becomes read-only."""
        self._transition_to(CompetitionStatus.COMPLETED, now=now)
        return [CompetitionCompleted(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Internal invariants & helpers
    # ------------------------------------------------------------------

    def _ensure_not_completed(self) -> None:
        if self._status is CompetitionStatus.COMPLETED:
            raise CompetitionAlreadyCompletedError("A completed competition is read-only.")

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

    def _pricing_added_event(
        self,
        combination: AdmissionCombination,
        price: Money,
        calculation_type: PricingCalculationType = PricingCalculationType.PER_PARTICIPANT,
    ) -> PricingRuleAdded:
        return PricingRuleAdded(
            aggregate_id=self._id.value,
            category_id=combination.category_id,
            discipline_id=combination.discipline_id,
            age_category_id=combination.age_category_id,
            participant_group_id=combination.participant_group_id,
            participation_format_id=combination.participation_format_id,
            amount=str(price.amount),
            currency=price.currency,
            calculation_type=calculation_type,
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

    def _require_participation_format(self, format_id: ParticipationFormatId) -> ParticipationFormat:
        participation_format = self._formats.get(format_id)
        if participation_format is None:
            raise ParticipationFormatNotFoundError(f"No participation format {format_id} in this competition.")
        return participation_format

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

    def _next_age_category_sort_order(self, participant_group_id: ParticipantGroupId) -> int:
        siblings = [a for a in self._age_categories.values() if a.participant_group_id == participant_group_id]
        if not siblings:
            return 0
        return max(a.sort_order for a in siblings) + 1

    def _next_participant_group_sort_order(self) -> int:
        if not self._participant_groups:
            return 0
        return max(g.sort_order for g in self._participant_groups.values()) + 1

    def _next_format_sort_order(self) -> int:
        if not self._formats:
            return 0
        return max(f.sort_order for f in self._formats.values()) + 1

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
