"""The Competition **template** aggregate — reusable competition configuration.

Many competitions reuse an identical constructor (the same categories, disciplines,
age bands, participant groups, participation formats, admission rules and prices).
A :class:`CompetitionTemplate` captures that configuration once, independently of
any competition, so :meth:`~apps.competitions.domain.entities.Competition.from_template`
can stamp out fresh drafts from it.

**Separate aggregate root, same invariants.** A template is its own consistency
boundary (its own identity, version and repository). It reuses the Competition's
child-entity types and rule value objects, and enforces the *same* referential and
uniqueness invariants via the shared helpers in
:mod:`apps.competitions.domain.entities` — a template can therefore never hold a
configuration a competition could not. It has **no lifecycle** (no DRAFT/PUBLISHED)
and emits **no domain events**: a template is an editing convenience, not a
business timeline. Regulations, documents and additional services are
competition-specific and are deliberately **not** part of a template.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only; time supplied by
the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from typing import Final

from .entities import (
    _SENTINEL,
    AgeCategory,
    Category,
    Discipline,
    ParticipantGroup,
    ParticipationFormat,
    _Unset,
    ensure_admission_combination_valid,
    ensure_age_range_free,
)
from .exceptions import (
    AdmissionRuleInUseError,
    AdmissionRuleNotFoundError,
    AgeCategoryInUseError,
    AgeCategoryNotFoundError,
    CategoryInUseError,
    CategoryNotFoundError,
    DirectConstructionError,
    DisciplineInUseError,
    DisciplineNotFoundError,
    DuplicateAdmissionRuleError,
    DuplicateAgeCategoryNameError,
    DuplicateCategoryError,
    DuplicateDisciplineError,
    DuplicateParticipantGroupError,
    DuplicateParticipationFormatError,
    DuplicatePricingRuleError,
    ParticipantGroupInUseError,
    ParticipantGroupNotFoundError,
    ParticipationFormatInUseError,
    ParticipationFormatNotFoundError,
    PricingRuleNotFoundError,
)
from .value_objects import (
    AdmissionCombination,
    AdmissionRule,
    AgeCategoryId,
    AgeCategoryName,
    AgeCategoryType,
    AgeRange,
    CategoryId,
    CategoryName,
    CompetitionDescription,
    DisciplineId,
    DisciplineName,
    MixedAgeCalculationMethod,
    Money,
    ParticipantCountRange,
    ParticipantGroupDescription,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormatDescription,
    ParticipationFormatId,
    ParticipationFormatName,
    PricingCalculationType,
    PricingRule,
    TemplateId,
    TemplateName,
)

__all__ = ["CompetitionTemplate"]

#: Opaque capability token proving construction went through a factory.
_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class CompetitionTemplate:
    """A reusable, validated competition configuration blueprint (aggregate root).

    Build it with the same ``add_*`` methods a competition uses; it enforces the
    same invariants. Equality/hashing is by :class:`TemplateId`.
    """

    _token: InitVar[object]
    _id: TemplateId
    _name: TemplateName
    _created_at: datetime
    _updated_at: datetime
    _description: CompetitionDescription | None = None
    _categories: dict[CategoryId, Category] = field(default_factory=dict)
    _disciplines: dict[DisciplineId, Discipline] = field(default_factory=dict)
    _age_categories: dict[AgeCategoryId, AgeCategory] = field(default_factory=dict)
    _participant_groups: dict[ParticipantGroupId, ParticipantGroup] = field(default_factory=dict)
    _formats: dict[ParticipationFormatId, ParticipationFormat] = field(default_factory=dict)
    _admission_rules: dict[AdmissionCombination, AdmissionRule] = field(default_factory=dict)
    _pricing_rules: dict[AdmissionCombination, PricingRule] = field(default_factory=dict)
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError("CompetitionTemplate must be created via CompetitionTemplate.create() or rehydrate(), not the constructor.")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        template_id: TemplateId,
        name: TemplateName,
        now: datetime,
        description: CompetitionDescription | None = None,
    ) -> CompetitionTemplate:
        """Create a new, empty template."""
        return cls(_token=_CREATION_TOKEN, _id=template_id, _name=name, _created_at=now, _updated_at=now, _description=description)

    @classmethod
    def rehydrate(
        cls,
        *,
        template_id: TemplateId,
        name: TemplateName,
        created_at: datetime,
        updated_at: datetime,
        description: CompetitionDescription | None = None,
        categories: Sequence[Category] = (),
        disciplines: Sequence[Discipline] = (),
        age_categories: Sequence[AgeCategory] = (),
        participant_groups: Sequence[ParticipantGroup] = (),
        formats: Sequence[ParticipationFormat] = (),
        admission_rules: Sequence[AdmissionRule] = (),
        pricing_rules: Sequence[PricingRule] = (),
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> CompetitionTemplate:
        """Reconstruct the aggregate from persistence (no re-validation)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=template_id,
            _name=name,
            _created_at=created_at,
            _updated_at=updated_at,
            _description=description,
            _categories={c.id: c for c in categories},
            _disciplines={d.id: d for d in disciplines},
            _age_categories={a.id: a for a in age_categories},
            _participant_groups={g.id: g for g in participant_groups},
            _formats={f.id: f for f in formats},
            _admission_rules={r.combination: r for r in admission_rules},
            _pricing_rules={p.combination: p for p in pricing_rules},
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Properties (read-only views consumed by Competition.from_template)
    # ------------------------------------------------------------------

    @property
    def id(self) -> TemplateId:
        return self._id

    @property
    def name(self) -> TemplateName:
        return self._name

    @property
    def description(self) -> CompetitionDescription | None:
        return self._description

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

    # ------------------------------------------------------------------
    # Taxonomy configuration
    # ------------------------------------------------------------------

    def add_category(self, *, category_id: CategoryId, name: CategoryName, now: datetime) -> Category:
        if any(c.name == name for c in self._categories.values()):
            raise DuplicateCategoryError(f"Жанр «{name.value}» уже есть.")
        category = Category.create(category_id=category_id, name=name)
        self._categories[category_id] = category
        self._touch(now)
        return category

    def remove_category(self, *, category_id: CategoryId, now: datetime) -> None:
        self._require_category(category_id)
        if any(d.category_id == category_id for d in self._disciplines.values()):
            raise CategoryInUseError("В этом жанре ещё есть номинации — сначала удалите их.")
        if any(c.category_id == category_id for c in self._admission_rules):
            raise CategoryInUseError("Жанр используется в правилах допуска — сначала уберите его оттуда.")
        if any(c.category_id == category_id for c in self._pricing_rules):
            raise CategoryInUseError("Жанр используется в правилах стоимости — сначала уберите его оттуда.")
        del self._categories[category_id]
        self._touch(now)

    def add_discipline(self, *, discipline_id: DisciplineId, category_id: CategoryId, name: DisciplineName, now: datetime) -> Discipline:
        self._require_category(category_id)
        if any(d.category_id == category_id and d.name == name for d in self._disciplines.values()):
            raise DuplicateDisciplineError(f"Номинация «{name.value}» в этом жанре уже есть.")
        discipline = Discipline.create(discipline_id=discipline_id, category_id=category_id, name=name)
        self._disciplines[discipline_id] = discipline
        self._touch(now)
        return discipline

    def remove_discipline(self, *, discipline_id: DisciplineId, now: datetime) -> None:
        self._require_discipline(discipline_id)
        if any(c.discipline_id == discipline_id for c in self._admission_rules):
            raise DisciplineInUseError("Номинация используется в правилах допуска — сначала уберите её оттуда.")
        if any(c.discipline_id == discipline_id for c in self._pricing_rules):
            raise DisciplineInUseError("Номинация используется в правилах стоимости — сначала уберите её оттуда.")
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
    ) -> AgeCategory:
        self._require_participant_group(participant_group_id)
        ensure_age_range_free(
            self._age_categories,
            age_range,
            participant_group_id=participant_group_id,
            age_category_type=age_category_type,
        )
        if any(a.participant_group_id == participant_group_id and a.name == name for a in self._age_categories.values()):
            raise DuplicateAgeCategoryNameError(f"Возрастная категория «{name.value}» в этом составе уже есть.")
        age_category = AgeCategory.create(
            age_category_id=age_category_id,
            participant_group_id=participant_group_id,
            name=name,
            age_range=age_range,
            age_category_type=age_category_type,
            mixed_calculation_method=mixed_calculation_method,
        )
        self._age_categories[age_category_id] = age_category
        self._touch(now)
        return age_category

    def remove_age_category(self, *, age_category_id: AgeCategoryId, now: datetime) -> None:
        self._require_age_category(age_category_id)
        if any(c.age_category_id == age_category_id for c in self._admission_rules):
            raise AgeCategoryInUseError("Возрастная категория используется в правилах допуска — сначала уберите её оттуда.")
        if any(c.age_category_id == age_category_id for c in self._pricing_rules):
            raise AgeCategoryInUseError("Возрастная категория используется в правилах стоимости — сначала уберите её оттуда.")
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
        sort_order: int = 0,
    ) -> ParticipantGroup:
        if any(g.name == name for g in self._participant_groups.values()):
            raise DuplicateParticipantGroupError(f"Состав участников «{name.value}» уже есть.")
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

    def remove_participant_group(self, *, participant_group_id: ParticipantGroupId, now: datetime) -> None:
        self._require_participant_group(participant_group_id)
        if any(a.participant_group_id == participant_group_id for a in self._age_categories.values()):
            raise ParticipantGroupInUseError("В этом составе ещё есть возрастные категории — сначала удалите их.")
        if any(c.participant_group_id == participant_group_id for c in self._admission_rules):
            raise ParticipantGroupInUseError("Состав участников используется в правилах допуска — сначала уберите его оттуда.")
        if any(c.participant_group_id == participant_group_id for c in self._pricing_rules):
            raise ParticipantGroupInUseError("Состав участников используется в правилах стоимости — сначала уберите его оттуда.")
        del self._participant_groups[participant_group_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Participation formats
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
    ) -> ParticipationFormat:
        if any(f.name == name for f in self._formats.values()):
            raise DuplicateParticipationFormatError(f"Форма участия «{name.value}» уже есть.")
        if sort_order is None:
            sort_order = self._next_format_sort_order()
        participation_format = ParticipationFormat.create(
            format_id=format_id,
            name=name,
            description=description,
            enabled=enabled,
            sort_order=sort_order,
        )
        self._formats[format_id] = participation_format
        self._touch(now)
        return participation_format

    def update_participation_format(
        self,
        *,
        format_id: ParticipationFormatId,
        now: datetime,
        name: ParticipationFormatName | None = None,
        description: ParticipationFormatDescription | None | _Unset = _SENTINEL,
        enabled: bool | None = None,
        sort_order: int | None = None,
    ) -> None:
        participation_format = self._require_participation_format(format_id)
        if name is not None and any(fid != format_id and f.name == name for fid, f in self._formats.items()):
            raise DuplicateParticipationFormatError(f"Форма участия «{name.value}» уже есть.")
        participation_format.update(
            name=name,
            description=description,
            enabled=enabled,
            sort_order=sort_order,
        )
        self._touch(now)

    def remove_participation_format(self, *, format_id: ParticipationFormatId, now: datetime) -> None:
        self._require_participation_format(format_id)
        if any(c.participation_format_id == format_id for c in self._admission_rules):
            raise ParticipationFormatInUseError("Форма участия используется в правилах допуска — сначала уберите её оттуда.")
        if any(c.participation_format_id == format_id for c in self._pricing_rules):
            raise ParticipationFormatInUseError("Форма участия используется в правилах стоимости — сначала уберите её оттуда.")
        del self._formats[format_id]
        self._touch(now)

    # ------------------------------------------------------------------
    # Admission & pricing rules
    # ------------------------------------------------------------------

    def add_admission_rule(self, *, combination: AdmissionCombination, now: datetime) -> AdmissionRule:
        self._validate_combination(combination)
        if combination in self._admission_rules:
            raise DuplicateAdmissionRuleError("Правило допуска для этого сочетания уже создано.")
        rule = AdmissionRule(combination=combination)
        self._admission_rules[combination] = rule
        self._touch(now)
        return rule

    def remove_admission_rule(self, *, combination: AdmissionCombination, now: datetime) -> None:
        if combination not in self._admission_rules:
            raise AdmissionRuleNotFoundError("Для этого сочетания нет правила допуска.")
        if combination in self._pricing_rules:
            raise AdmissionRuleInUseError("Для этого сочетания задана стоимость — сначала удалите цену.")
        del self._admission_rules[combination]
        self._touch(now)

    def add_pricing_rule(
        self,
        *,
        combination: AdmissionCombination,
        price_per_participant: Money,
        now: datetime,
        calculation_type: PricingCalculationType = PricingCalculationType.PER_PARTICIPANT,
    ) -> PricingRule:
        self._validate_combination(combination)
        if combination not in self._admission_rules:
            raise AdmissionRuleNotFoundError("Нельзя назначить цену сочетанию, которое не допущено.")
        if combination in self._pricing_rules:
            raise DuplicatePricingRuleError("Стоимость для этого сочетания уже задана.")
        rule = PricingRule(
            combination=combination,
            price_per_participant=price_per_participant,
            calculation_type=calculation_type,
        )
        self._pricing_rules[combination] = rule
        self._touch(now)
        return rule

    def remove_pricing_rule(self, *, combination: AdmissionCombination, now: datetime) -> None:
        if combination not in self._pricing_rules:
            raise PricingRuleNotFoundError("Для этого сочетания стоимость не задана.")
        del self._pricing_rules[combination]
        self._touch(now)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_category(self, category_id: CategoryId) -> Category:
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError("Такого жанра в шаблоне нет.")
        return category

    def _require_discipline(self, discipline_id: DisciplineId) -> Discipline:
        discipline = self._disciplines.get(discipline_id)
        if discipline is None:
            raise DisciplineNotFoundError("Такой номинации в шаблоне нет.")
        return discipline

    def _require_age_category(self, age_category_id: AgeCategoryId) -> AgeCategory:
        age_category = self._age_categories.get(age_category_id)
        if age_category is None:
            raise AgeCategoryNotFoundError("Такой возрастной категории в шаблоне нет.")
        return age_category

    def _require_participant_group(self, participant_group_id: ParticipantGroupId) -> ParticipantGroup:
        group = self._participant_groups.get(participant_group_id)
        if group is None:
            raise ParticipantGroupNotFoundError("Такого состава участников в шаблоне нет.")
        return group

    def _require_participation_format(self, format_id: ParticipationFormatId) -> ParticipationFormat:
        participation_format = self._formats.get(format_id)
        if participation_format is None:
            raise ParticipationFormatNotFoundError("Такой формы участия в шаблоне нет.")
        return participation_format

    def _validate_combination(self, combination: AdmissionCombination) -> None:
        ensure_admission_combination_valid(
            combination,
            categories=self._categories,
            disciplines=self._disciplines,
            age_categories=self._age_categories,
            participant_groups=self._participant_groups,
            formats=self._formats,
        )

    def _next_format_sort_order(self) -> int:
        if not self._formats:
            return 0
        return max(f.sort_order for f in self._formats.values()) + 1

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompetitionTemplate) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"CompetitionTemplate(id={self._id!r}, name={self._name.value!r})"
