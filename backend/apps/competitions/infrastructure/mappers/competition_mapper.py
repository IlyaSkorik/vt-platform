"""``CompetitionMapper`` — the ACL between the ``Competition`` aggregate and its rows.

The **single** component that knows both the framework-free domain
(:class:`apps.competitions.domain.entities.Competition` and its value objects) and
the Django persistence models. Keeping that knowledge here is what lets the domain
stay ignorant of the ORM and the ORM stay ignorant of business rules (ARCH-001
§4.1, §7.2, §14).

Its whole job is translation:

* :meth:`to_domain` — a competition row **plus all its child rows** → aggregate,
  via :meth:`Competition.rehydrate` (no re-validation, no events, ``version`` kept).
* :meth:`to_model` — aggregate → a **new, unsaved** root ``CompetitionModel``.
* :meth:`to_*_models` — the aggregate's child collections → **unsaved** child rows
  keyed to the competition, for the repository to synchronize.

Child rows are written with the **domain child id** as their primary key, so ids
stay stable across the repository's delete-and-recreate synchronization. Admission
and pricing rules are value objects without a domain id, so their synthetic row
key is left to default. What the mapper deliberately does **not** do: validate,
run workflows, publish events, query, or call ``save()``.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.competitions.domain.entities import (
    AdditionalService,
    AgeCategory,
    Category,
    Competition,
    CompetitionDocument,
    CompetitionRegulation,
    Contact,
    Discipline,
    InformationBlock,
    ParticipantGroup,
    ParticipationFormat,
)
from apps.competitions.domain.value_objects import (
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
    CompetitionStatus,
    CompetitionTitle,
    ContactId,
    ContactType,
    ContactValue,
    Currency,
    DateRange,
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
    RegistrationDeadlines,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    RichTextFormat,
    Season,
    ServiceBillingModel,
    ServiceDescription,
    ServiceId,
    ServiceName,
    Venue,
)
from apps.competitions.infrastructure.mappers.settings_json import settings_from_json, settings_to_json
from apps.competitions.infrastructure.models import (
    AdditionalServiceModel,
    AdmissionRuleModel,
    AgeCategoryModel,
    CategoryModel,
    CompetitionModel,
    ContactModel,
    DisciplineModel,
    DocumentModel,
    InformationBlockModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
    PricingRuleModel,
    RegulationModel,
)

__all__ = ["CompetitionChildRows", "CompetitionMapper"]


class CompetitionChildRows:
    """The unsaved child rows of one competition, grouped for the repository to sync."""

    __slots__ = (
        "additional_services",
        "admission_rules",
        "age_categories",
        "categories",
        "contacts",
        "disciplines",
        "documents",
        "information_blocks",
        "participant_groups",
        "participation_formats",
        "pricing_rules",
        "regulations",
    )

    def __init__(
        self,
        *,
        categories: list[CategoryModel],
        disciplines: list[DisciplineModel],
        age_categories: list[AgeCategoryModel],
        participant_groups: list[ParticipantGroupModel],
        participation_formats: list[ParticipationFormatModel],
        admission_rules: list[AdmissionRuleModel],
        pricing_rules: list[PricingRuleModel],
        regulations: list[RegulationModel],
        documents: list[DocumentModel],
        additional_services: list[AdditionalServiceModel],
        contacts: list[ContactModel],
        information_blocks: list[InformationBlockModel],
    ) -> None:
        self.categories = categories
        self.disciplines = disciplines
        self.age_categories = age_categories
        self.participant_groups = participant_groups
        self.participation_formats = participation_formats
        self.admission_rules = admission_rules
        self.pricing_rules = pricing_rules
        self.regulations = regulations
        self.documents = documents
        self.additional_services = additional_services
        self.contacts = contacts
        self.information_blocks = information_blocks


class CompetitionMapper:
    """Bidirectional translator between the ``Competition`` aggregate and its rows."""

    # ------------------------------------------------------------------
    # Rows → aggregate
    # ------------------------------------------------------------------

    @staticmethod
    def to_domain(
        model: CompetitionModel,
        *,
        categories: Iterable[CategoryModel] = (),
        disciplines: Iterable[DisciplineModel] = (),
        age_categories: Iterable[AgeCategoryModel] = (),
        participant_groups: Iterable[ParticipantGroupModel] = (),
        participation_formats: Iterable[ParticipationFormatModel] = (),
        admission_rules: Iterable[AdmissionRuleModel] = (),
        pricing_rules: Iterable[PricingRuleModel] = (),
        regulations: Iterable[RegulationModel] = (),
        documents: Iterable[DocumentModel] = (),
        additional_services: Iterable[AdditionalServiceModel] = (),
        contacts: Iterable[ContactModel] = (),
        information_blocks: Iterable[InformationBlockModel] = (),
    ) -> Competition:
        """Reconstruct the aggregate from its root row and all child rows."""
        return Competition.rehydrate(
            competition_id=CompetitionId.from_uuid(model.id),
            title=CompetitionTitle(model.title),
            season=Season(model.season),
            organizer_id=OrganizerId.from_uuid(model.organizer_id),
            status=CompetitionStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            description=(CompetitionDescription(model.description) if model.description else None),
            branding=CompetitionBranding(
                logo=FileReference(model.logo) if model.logo else None,
                banner=FileReference(model.banner) if model.banner else None,
                poster=FileReference(model.poster) if model.poster else None,
            ),
            venue=(Venue(name=model.venue_name, address=model.venue_address) if model.venue_name else None),
            registration_period=(
                DateRange(start=model.registration_start, end=model.registration_end)
                if model.registration_start is not None and model.registration_end is not None
                else None
            ),
            competition_period=(
                DateRange(start=model.competition_start, end=model.competition_end)
                if model.competition_start is not None and model.competition_end is not None
                else None
            ),
            settings=settings_from_json(model.settings),
            deadlines=RegistrationDeadlines(
                application=model.deadline_application,
                payment=model.deadline_payment,
                music_upload=model.deadline_music_upload,
                document_upload=model.deadline_document_upload,
                correction=model.deadline_correction,
            ),
            categories=[
                Category.rehydrate(
                    category_id=CategoryId.from_uuid(row.id),
                    name=CategoryName(row.name),
                    description=CategoryDescription(row.description) if row.description else None,
                    sort_order=row.sort_order,
                )
                for row in categories
            ],
            disciplines=[
                Discipline.rehydrate(
                    discipline_id=DisciplineId.from_uuid(row.id),
                    category_id=CategoryId.from_uuid(row.category_id),
                    name=DisciplineName(row.name),
                    sort_order=row.sort_order,
                )
                for row in disciplines
            ],
            age_categories=[
                AgeCategory.rehydrate(
                    age_category_id=AgeCategoryId.from_uuid(row.id),
                    category_id=CategoryId.from_uuid(row.category_id),
                    name=AgeCategoryName(row.name),
                    age_range=AgeRange(row.min_age, row.max_age),
                    age_category_type=AgeCategoryType(row.type) if row.type else AgeCategoryType.STANDARD,
                    mixed_calculation_method=(
                        MixedAgeCalculationMethod(row.mixed_calculation_method) if row.mixed_calculation_method else None
                    ),
                    sort_order=row.sort_order,
                )
                for row in age_categories
            ],
            participant_groups=[
                ParticipantGroup.rehydrate(
                    participant_group_id=ParticipantGroupId.from_uuid(row.id),
                    category_id=CategoryId.from_uuid(row.category_id),
                    name=ParticipantGroupName(row.name),
                    count_range=ParticipantCountRange(row.min_count, row.max_count),
                    description=ParticipantGroupDescription(row.description) if row.description else None,
                    sort_order=row.sort_order,
                )
                for row in participant_groups
            ],
            formats=[
                ParticipationFormat.rehydrate(
                    format_id=ParticipationFormatId.from_uuid(row.id),
                    name=ParticipationFormatName(row.name),
                    description=ParticipationFormatDescription(row.description) if row.description else None,
                    enabled=row.enabled,
                    sort_order=row.sort_order,
                )
                for row in participation_formats
            ],
            admission_rules=[AdmissionRule(combination=_combination(row)) for row in admission_rules],
            pricing_rules=[
                PricingRule(
                    combination=_combination(row),
                    price_per_participant=Money(amount=row.amount, currency=Currency(row.currency)),
                    calculation_type=PricingCalculationType(row.calculation_type),
                )
                for row in pricing_rules
            ],
            regulations=[
                CompetitionRegulation.rehydrate(
                    regulation_id=RegulationId.from_uuid(row.id),
                    title=RegulationTitle(row.title),
                    version=RegulationVersion(row.document_version),
                    publication_date=row.publication_date,
                    file=FileReference(row.file_reference),
                )
                for row in regulations
            ],
            current_regulation_id=(RegulationId.from_uuid(model.current_regulation_id) if model.current_regulation_id is not None else None),
            documents=[
                CompetitionDocument.rehydrate(
                    document_id=DocumentId.from_uuid(row.id),
                    title=DocumentTitle(row.title),
                    category=DocumentCategory(row.category),
                    visibility=DocumentVisibility(row.visibility),
                    file=FileReference(row.file_reference),
                    description=DocumentDescription(row.description) if row.description else None,
                    sort_order=row.sort_order,
                    published=row.published,
                )
                for row in documents
            ],
            additional_services=[
                AdditionalService.rehydrate(
                    service_id=ServiceId.from_uuid(row.id),
                    name=ServiceName(row.name),
                    price=Money(amount=row.amount, currency=Currency(row.currency)),
                    description=ServiceDescription(row.description) if row.description else None,
                    billing_model=ServiceBillingModel(row.billing_model),
                    available_format_ids=[
                        ParticipationFormatId.from_string(str(format_id)) for format_id in (row.available_format_ids or [])
                    ],
                    required=row.required,
                    enabled=row.enabled,
                    sort_order=row.sort_order,
                )
                for row in additional_services
            ],
            contacts=[
                Contact.rehydrate(
                    contact_id=ContactId.from_uuid(row.id),
                    contact_type=ContactType(row.contact_type),
                    value=ContactValue(row.value),
                    is_primary=row.is_primary,
                )
                for row in contacts
            ],
            information_blocks=[
                InformationBlock.rehydrate(
                    block_id=InformationBlockId.from_uuid(row.id),
                    title=InformationBlockTitle(row.title),
                    content=RichText(row.content, RichTextFormat(row.content_format)),
                    published=row.published,
                    sort_order=row.sort_order,
                )
                for row in information_blocks
            ],
            deleted_at=model.deleted_at,
            version=model.version,
        )

    # ------------------------------------------------------------------
    # Aggregate → root row
    # ------------------------------------------------------------------

    @staticmethod
    def to_model(entity: Competition) -> CompetitionModel:
        """Build a brand-new, **unsaved** root ``CompetitionModel`` from an aggregate."""
        return CompetitionModel(**CompetitionMapper._to_columns(entity))

    @staticmethod
    def _to_columns(entity: Competition) -> dict[str, object]:
        """Flatten an aggregate into the root ``CompetitionModel`` column values."""
        branding = entity.branding
        venue = entity.venue
        registration = entity.registration_period
        competition = entity.competition_period
        deadlines = entity.deadlines
        current_regulation = entity.current_regulation
        return {
            "id": entity.id.value,
            "title": entity.title.value,
            "season": entity.season.value,
            "organizer_id": entity.organizer_id.value,
            "status": entity.status.value,
            "description": entity.description.value if entity.description is not None else None,
            "logo": branding.logo.value if branding.logo is not None else None,
            "banner": branding.banner.value if branding.banner is not None else None,
            "poster": branding.poster.value if branding.poster is not None else None,
            "venue_name": venue.name if venue is not None else None,
            "venue_address": venue.address if venue is not None else None,
            "registration_start": registration.start if registration is not None else None,
            "registration_end": registration.end if registration is not None else None,
            "competition_start": competition.start if competition is not None else None,
            "competition_end": competition.end if competition is not None else None,
            "deadline_application": deadlines.application,
            "deadline_payment": deadlines.payment,
            "deadline_music_upload": deadlines.music_upload,
            "deadline_document_upload": deadlines.document_upload,
            "deadline_correction": deadlines.correction,
            "settings": settings_to_json(entity.settings),
            "current_regulation_id": current_regulation.id.value if current_regulation is not None else None,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "version": entity.version,
        }

    # ------------------------------------------------------------------
    # Aggregate → child rows
    # ------------------------------------------------------------------

    @staticmethod
    def to_child_rows(entity: Competition) -> CompetitionChildRows:
        """Build every unsaved child row of ``entity``, keyed to the competition."""
        competition_id = entity.id.value
        return CompetitionChildRows(
            categories=[
                CategoryModel(
                    id=c.id.value,
                    competition_id=competition_id,
                    name=c.name.value,
                    description=c.description.value if c.description is not None else None,
                    sort_order=c.sort_order,
                )
                for c in entity.categories
            ],
            disciplines=[
                DisciplineModel(
                    id=d.id.value,
                    competition_id=competition_id,
                    category_id=d.category_id.value,
                    name=d.name.value,
                    sort_order=d.sort_order,
                )
                for d in entity.disciplines
            ],
            age_categories=[
                AgeCategoryModel(
                    id=a.id.value,
                    competition_id=competition_id,
                    category_id=a.category_id.value,
                    name=a.name.value,
                    min_age=a.age_range.min_age,
                    max_age=a.age_range.max_age,
                    sort_order=a.sort_order,
                    type=a.type.value,
                    mixed_calculation_method=a.mixed_calculation_method.value if a.mixed_calculation_method is not None else None,
                )
                for a in entity.age_categories
            ],
            participant_groups=[
                ParticipantGroupModel(
                    id=g.id.value,
                    competition_id=competition_id,
                    category_id=g.category_id.value,
                    name=g.name.value,
                    min_count=g.count_range.min_count,
                    max_count=g.count_range.max_count,
                    description=g.description.value if g.description is not None else None,
                    sort_order=g.sort_order,
                )
                for g in entity.participant_groups
            ],
            participation_formats=[
                ParticipationFormatModel(
                    id=f.id.value,
                    competition_id=competition_id,
                    name=f.name.value,
                    description=f.description.value if f.description is not None else None,
                    enabled=f.enabled,
                    sort_order=f.sort_order,
                )
                for f in entity.participation_formats
            ],
            admission_rules=[
                AdmissionRuleModel(
                    competition_id=competition_id,
                    category_id=r.combination.category_id.value,
                    discipline_id=r.combination.discipline_id.value,
                    age_category_id=r.combination.age_category_id.value,
                    participant_group_id=r.combination.participant_group_id.value,
                    participation_format_id=r.combination.participation_format_id.value,
                )
                for r in entity.admission_rules
            ],
            pricing_rules=[
                PricingRuleModel(
                    competition_id=competition_id,
                    category_id=p.combination.category_id.value,
                    discipline_id=p.combination.discipline_id.value,
                    age_category_id=p.combination.age_category_id.value,
                    participant_group_id=p.combination.participant_group_id.value,
                    participation_format_id=p.combination.participation_format_id.value,
                    amount=p.price_per_participant.amount,
                    currency=p.price_per_participant.currency.value,
                    calculation_type=p.calculation_type.value,
                )
                for p in entity.pricing_rules
            ],
            regulations=[
                RegulationModel(
                    id=r.id.value,
                    competition_id=competition_id,
                    title=r.title.value,
                    document_version=r.version.value,
                    publication_date=r.publication_date,
                    file_reference=r.file.value,
                )
                for r in entity.regulations
            ],
            documents=[
                DocumentModel(
                    id=d.id.value,
                    competition_id=competition_id,
                    title=d.title.value,
                    category=d.category.value,
                    visibility=d.visibility.value,
                    file_reference=d.file.value,
                    description=d.description.value if d.description is not None else None,
                    sort_order=d.sort_order,
                    published=d.is_published,
                )
                for d in entity.documents
            ],
            additional_services=[
                AdditionalServiceModel(
                    id=s.id.value,
                    competition_id=competition_id,
                    name=s.name.value,
                    amount=s.price.amount,
                    currency=s.price.currency.value,
                    description=s.description.value if s.description is not None else None,
                    billing_model=s.billing_model.value,
                    available_format_ids=[fid.json() for fid in sorted(s.available_format_ids, key=lambda x: x.json())],
                    required=s.required,
                    enabled=s.is_enabled,
                    sort_order=s.sort_order,
                )
                for s in entity.additional_services
            ],
            contacts=[
                ContactModel(
                    id=c.id.value,
                    competition_id=competition_id,
                    contact_type=c.type.value,
                    value=c.value.value,
                    is_primary=c.is_primary,
                )
                for c in entity.contacts
            ],
            information_blocks=[
                InformationBlockModel(
                    id=b.id.value,
                    competition_id=competition_id,
                    title=b.title.value,
                    content=b.content.value,
                    content_format=b.content.format.value,
                    published=b.is_published,
                    sort_order=b.sort_order,
                )
                for b in entity.information_blocks
            ],
        )


def _combination(row: AdmissionRuleModel | PricingRuleModel) -> AdmissionCombination:
    """Rebuild the five-part admission combination from a rule row."""
    return AdmissionCombination(
        category_id=CategoryId.from_uuid(row.category_id),
        discipline_id=DisciplineId.from_uuid(row.discipline_id),
        age_category_id=AgeCategoryId.from_uuid(row.age_category_id),
        participant_group_id=ParticipantGroupId.from_uuid(row.participant_group_id),
        participation_format_id=ParticipationFormatId.from_uuid(row.participation_format_id),
    )
