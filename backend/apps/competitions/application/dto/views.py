"""Output view DTOs for the Competitions application layer.

Immutable, primitive-only projections of the :class:`Competition` aggregate. They
are the boundary in the *outward* direction: handlers render the aggregate into
flat, serialization-agnostic shapes so no outer layer needs to import the domain to
read a result. Enums are rendered as their string values, ids as canonical UUID
strings, money as a decimal string, so the presentation edge maps them 1:1 onto the
API wire shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

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
from apps.competitions.domain.value_objects import AdmissionRule, CompetitionSettings, PricingRule

__all__ = [
    "AddedChildResult",
    "AdditionalServiceView",
    "AdmissionRuleView",
    "AgeCategoryView",
    "BrandingView",
    "CategoryView",
    "CompetitionDetailView",
    "CompetitionSummaryView",
    "ContactView",
    "DeadlinesView",
    "DisciplineView",
    "DocumentView",
    "InformationBlockView",
    "ParticipantGroupView",
    "ParticipationFormatView",
    "PeriodView",
    "PricingRuleView",
    "PublicationReportView",
    "RegulationView",
    "SettingsView",
    "VenueView",
]


@dataclass(frozen=True, slots=True)
class VenueView:
    name: str
    address: str | None


@dataclass(frozen=True, slots=True)
class PeriodView:
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class BrandingView:
    logo: str | None
    banner: str | None
    poster: str | None


@dataclass(frozen=True, slots=True)
class DeadlinesView:
    application: datetime | None
    payment: datetime | None
    music_upload: datetime | None
    document_upload: datetime | None
    correction: datetime | None


@dataclass(frozen=True, slots=True)
class MusicRequirementsView:
    require_upload: bool
    allow_replacement: bool
    allowed_formats: tuple[str, ...]
    max_upload_size_mb: int


@dataclass(frozen=True, slots=True)
class VideoRequirementsView:
    mode: str
    allowed_providers: tuple[str, ...]
    allow_replacement: bool


@dataclass(frozen=True, slots=True)
class PaymentReceiptRequirementsView:
    require_receipt: bool
    allow_upload_later: bool
    allow_replacement: bool


@dataclass(frozen=True, slots=True)
class FormatRequirementsView:
    participation_format_id: str
    music: MusicRequirementsView
    video: VideoRequirementsView
    payment_receipt: PaymentReceiptRequirementsView


@dataclass(frozen=True, slots=True)
class SettingsView:
    allow_multiple_applications: bool
    allow_application_editing: bool
    allow_withdrawing_applications: bool
    allow_copying_previous_applications: bool
    require_teacher: bool
    require_parent_guardian: bool
    participant_comment_enabled: bool
    require_document_upload: bool
    allow_additional_documents_later: bool
    allow_replacing_documents: bool
    payment_required: bool
    payment_timing: str
    payment_methods: tuple[str, ...]
    require_personal_data_consent: bool
    require_media_consent: bool
    require_regulations_acceptance: bool
    email_notifications: bool
    cabinet_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    manual_application_approval: bool
    automatic_approval_after_payment: bool
    allow_returning_for_correction: bool
    format_requirements: tuple[FormatRequirementsView, ...]

    @classmethod
    def of(cls, settings: CompetitionSettings) -> SettingsView:
        return cls(
            allow_multiple_applications=settings.allow_multiple_applications,
            allow_application_editing=settings.allow_application_editing,
            allow_withdrawing_applications=settings.allow_withdrawing_applications,
            allow_copying_previous_applications=settings.allow_copying_previous_applications,
            require_teacher=settings.require_teacher,
            require_parent_guardian=settings.require_parent_guardian,
            participant_comment_enabled=settings.participant_comment_enabled,
            require_document_upload=settings.require_document_upload,
            allow_additional_documents_later=settings.allow_additional_documents_later,
            allow_replacing_documents=settings.allow_replacing_documents,
            payment_required=settings.payment_required,
            payment_timing=settings.payment_timing.value,
            payment_methods=tuple(method.value for method in settings.payment_methods),
            require_personal_data_consent=settings.require_personal_data_consent,
            require_media_consent=settings.require_media_consent,
            require_regulations_acceptance=settings.require_regulations_acceptance,
            email_notifications=settings.email_notifications,
            cabinet_notifications=settings.cabinet_notifications,
            sms_notifications=settings.sms_notifications,
            push_notifications=settings.push_notifications,
            manual_application_approval=settings.manual_application_approval,
            automatic_approval_after_payment=settings.automatic_approval_after_payment,
            allow_returning_for_correction=settings.allow_returning_for_correction,
            format_requirements=tuple(
                FormatRequirementsView(
                    participation_format_id=item.participation_format_id.json(),
                    music=MusicRequirementsView(
                        require_upload=item.music.require_upload,
                        allow_replacement=item.music.allow_replacement,
                        allowed_formats=item.music.allowed_formats,
                        max_upload_size_mb=item.music.max_upload_size_mb,
                    ),
                    video=VideoRequirementsView(
                        mode=item.video.mode.value,
                        allowed_providers=tuple(provider.value for provider in item.video.allowed_providers),
                        allow_replacement=item.video.allow_replacement,
                    ),
                    payment_receipt=PaymentReceiptRequirementsView(
                        require_receipt=item.payment_receipt.require_receipt,
                        allow_upload_later=item.payment_receipt.allow_upload_later,
                        allow_replacement=item.payment_receipt.allow_replacement,
                    ),
                )
                for item in settings.format_requirements
            ),
        )


@dataclass(frozen=True, slots=True)
class CategoryView:
    id: str
    name: str
    description: str | None
    sort_order: int

    @classmethod
    def of(cls, category: Category) -> CategoryView:
        return cls(
            id=category.id.json(),
            name=category.name.value,
            description=category.description.value if category.description is not None else None,
            sort_order=category.sort_order,
        )


@dataclass(frozen=True, slots=True)
class DisciplineView:
    id: str
    category_id: str
    name: str
    sort_order: int

    @classmethod
    def of(cls, discipline: Discipline) -> DisciplineView:
        return cls(
            id=discipline.id.json(),
            category_id=discipline.category_id.json(),
            name=discipline.name.value,
            sort_order=discipline.sort_order,
        )


@dataclass(frozen=True, slots=True)
class AgeCategoryView:
    id: str
    category_id: str
    name: str
    min_age: int
    max_age: int
    sort_order: int
    type: str
    mixed_calculation_method: str | None

    @classmethod
    def of(cls, age_category: AgeCategory) -> AgeCategoryView:
        return cls(
            id=age_category.id.json(),
            category_id=age_category.category_id.json(),
            name=age_category.name.value,
            min_age=age_category.age_range.min_age,
            max_age=age_category.age_range.max_age,
            sort_order=age_category.sort_order,
            type=age_category.type.value,
            mixed_calculation_method=age_category.mixed_calculation_method.value if age_category.mixed_calculation_method is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ParticipantGroupView:
    id: str
    category_id: str
    name: str
    min_count: int
    max_count: int | None
    description: str | None
    sort_order: int

    @classmethod
    def of(cls, group: ParticipantGroup) -> ParticipantGroupView:
        return cls(
            id=group.id.json(),
            category_id=group.category_id.json(),
            name=group.name.value,
            min_count=group.count_range.min_count,
            max_count=group.count_range.max_count,
            description=group.description.value if group.description is not None else None,
            sort_order=group.sort_order,
        )


@dataclass(frozen=True, slots=True)
class ParticipationFormatView:
    id: str
    name: str
    description: str | None
    enabled: bool
    sort_order: int

    @classmethod
    def of(cls, participation_format: ParticipationFormat) -> ParticipationFormatView:
        return cls(
            id=participation_format.id.json(),
            name=participation_format.name.value,
            description=participation_format.description.value if participation_format.description is not None else None,
            enabled=participation_format.enabled,
            sort_order=participation_format.sort_order,
        )


@dataclass(frozen=True, slots=True)
class AdmissionRuleView:
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str

    @classmethod
    def of(cls, rule: AdmissionRule) -> AdmissionRuleView:
        c = rule.combination
        return cls(
            category_id=c.category_id.json(),
            discipline_id=c.discipline_id.json(),
            age_category_id=c.age_category_id.json(),
            participant_group_id=c.participant_group_id.json(),
            participation_format_id=c.participation_format_id.json(),
        )


@dataclass(frozen=True, slots=True)
class PricingRuleView:
    category_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str
    amount: str
    currency: str
    calculation_type: str

    @classmethod
    def of(cls, rule: PricingRule) -> PricingRuleView:
        c = rule.combination
        return cls(
            category_id=c.category_id.json(),
            discipline_id=c.discipline_id.json(),
            age_category_id=c.age_category_id.json(),
            participant_group_id=c.participant_group_id.json(),
            participation_format_id=c.participation_format_id.json(),
            amount=str(rule.price_per_participant.amount),
            currency=rule.price_per_participant.currency.value,
            calculation_type=rule.calculation_type.value,
        )


@dataclass(frozen=True, slots=True)
class RegulationView:
    id: str
    title: str
    version: str
    publication_date: date
    file_reference: str
    is_current: bool

    @classmethod
    def of(cls, regulation: CompetitionRegulation, *, is_current: bool) -> RegulationView:
        return cls(
            id=regulation.id.json(),
            title=regulation.title.value,
            version=regulation.version.value,
            publication_date=regulation.publication_date,
            file_reference=regulation.file.value,
            is_current=is_current,
        )


@dataclass(frozen=True, slots=True)
class DocumentView:
    id: str
    title: str
    category: str
    visibility: str
    file_reference: str
    description: str | None
    sort_order: int
    published: bool

    @classmethod
    def of(cls, document: CompetitionDocument) -> DocumentView:
        return cls(
            id=document.id.json(),
            title=document.title.value,
            category=document.category.value,
            visibility=document.visibility.value,
            file_reference=document.file.value,
            description=document.description.value if document.description is not None else None,
            sort_order=document.sort_order,
            published=document.is_published,
        )


@dataclass(frozen=True, slots=True)
class AdditionalServiceView:
    id: str
    name: str
    amount: str
    currency: str
    description: str | None
    billing_model: str
    participation_format_ids: tuple[str, ...]
    required: bool
    enabled: bool
    sort_order: int

    @classmethod
    def of(cls, service: AdditionalService) -> AdditionalServiceView:
        return cls(
            id=service.id.json(),
            name=service.name.value,
            amount=str(service.price.amount),
            currency=service.price.currency.value,
            description=service.description.value if service.description is not None else None,
            billing_model=service.billing_model.value,
            participation_format_ids=tuple(
                sorted(fid.json() for fid in service.available_format_ids),
            ),
            required=service.required,
            enabled=service.is_enabled,
            sort_order=service.sort_order,
        )


@dataclass(frozen=True, slots=True)
class ContactView:
    id: str
    type: str
    value: str
    is_primary: bool

    @classmethod
    def of(cls, contact: Contact) -> ContactView:
        return cls(id=contact.id.json(), type=contact.type.value, value=contact.value.value, is_primary=contact.is_primary)


@dataclass(frozen=True, slots=True)
class InformationBlockView:
    id: str
    title: str
    content: str
    content_format: str
    published: bool
    sort_order: int

    @classmethod
    def of(cls, block: InformationBlock) -> InformationBlockView:
        return cls(
            id=block.id.json(),
            title=block.title.value,
            content=block.content.value,
            content_format=block.content.format.value,
            published=block.is_published,
            sort_order=block.sort_order,
        )


@dataclass(frozen=True, slots=True)
class PublicationIssueView:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PublicationReportView:
    is_publishable: bool
    errors: tuple[PublicationIssueView, ...]
    warnings: tuple[PublicationIssueView, ...]

    @classmethod
    def of(cls, competition: Competition) -> PublicationReportView:
        report = competition.publication_report()
        return cls(
            is_publishable=report.is_publishable,
            errors=tuple(PublicationIssueView(code=i.code.value, message=i.message) for i in report.errors),
            warnings=tuple(PublicationIssueView(code=i.code.value, message=i.message) for i in report.warnings),
        )


@dataclass(frozen=True, slots=True)
class CompetitionSummaryView:
    """A flat list-item projection of a competition (no child collections)."""

    id: str
    title: str
    season: str
    status: str
    organizer_id: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def of(cls, competition: Competition) -> CompetitionSummaryView:
        return cls(
            id=competition.id.json(),
            title=competition.title.value,
            season=competition.season.value,
            status=competition.status.value,
            organizer_id=competition.organizer_id.json(),
            description=competition.description.value if competition.description is not None else None,
            created_at=competition.created_at,
            updated_at=competition.updated_at,
            version=competition.version,
        )


@dataclass(frozen=True, slots=True)
class CompetitionDetailView:
    """The full projection of a competition aggregate, child collections included."""

    id: str
    title: str
    season: str
    status: str
    organizer_id: str
    description: str | None
    branding: BrandingView
    venue: VenueView | None
    registration_period: PeriodView | None
    competition_period: PeriodView | None
    settings: SettingsView
    deadlines: DeadlinesView
    participation_formats: tuple[ParticipationFormatView, ...]
    categories: tuple[CategoryView, ...]
    disciplines: tuple[DisciplineView, ...]
    age_categories: tuple[AgeCategoryView, ...]
    participant_groups: tuple[ParticipantGroupView, ...]
    admission_rules: tuple[AdmissionRuleView, ...]
    pricing_rules: tuple[PricingRuleView, ...]
    regulations: tuple[RegulationView, ...]
    current_regulation_id: str | None
    documents: tuple[DocumentView, ...]
    additional_services: tuple[AdditionalServiceView, ...]
    contacts: tuple[ContactView, ...]
    information_blocks: tuple[InformationBlockView, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def of(cls, competition: Competition) -> CompetitionDetailView:
        current = competition.current_regulation
        current_id = current.id if current is not None else None
        settings = competition.settings
        deadlines = competition.deadlines
        branding = competition.branding
        venue = competition.venue
        registration = competition.registration_period
        period = competition.competition_period
        return cls(
            id=competition.id.json(),
            title=competition.title.value,
            season=competition.season.value,
            status=competition.status.value,
            organizer_id=competition.organizer_id.json(),
            description=competition.description.value if competition.description is not None else None,
            branding=BrandingView(
                logo=branding.logo.value if branding.logo is not None else None,
                banner=branding.banner.value if branding.banner is not None else None,
                poster=branding.poster.value if branding.poster is not None else None,
            ),
            venue=VenueView(name=venue.name, address=venue.address) if venue is not None else None,
            registration_period=PeriodView(start=registration.start, end=registration.end) if registration is not None else None,
            competition_period=PeriodView(start=period.start, end=period.end) if period is not None else None,
            settings=SettingsView.of(settings),
            deadlines=DeadlinesView(
                application=deadlines.application,
                payment=deadlines.payment,
                music_upload=deadlines.music_upload,
                document_upload=deadlines.document_upload,
                correction=deadlines.correction,
            ),
            participation_formats=tuple(ParticipationFormatView.of(f) for f in competition.participation_formats),
            categories=tuple(CategoryView.of(c) for c in competition.categories),
            disciplines=tuple(DisciplineView.of(d) for d in competition.disciplines),
            age_categories=tuple(AgeCategoryView.of(a) for a in competition.age_categories),
            participant_groups=tuple(ParticipantGroupView.of(g) for g in competition.participant_groups),

            admission_rules=tuple(AdmissionRuleView.of(r) for r in competition.admission_rules),
            pricing_rules=tuple(PricingRuleView.of(p) for p in competition.pricing_rules),
            regulations=tuple(RegulationView.of(r, is_current=r.id == current_id) for r in competition.regulations),
            current_regulation_id=current_id.json() if current_id is not None else None,
            documents=tuple(DocumentView.of(d) for d in competition.documents),
            additional_services=tuple(AdditionalServiceView.of(s) for s in competition.additional_services),
            contacts=tuple(ContactView.of(c) for c in competition.contacts),
            information_blocks=tuple(InformationBlockView.of(b) for b in competition.information_blocks),
            created_at=competition.created_at,
            updated_at=competition.updated_at,
            version=competition.version,
        )


@dataclass(frozen=True, slots=True)
class AddedChildResult:
    """The outcome of an add-child command: the new child id plus the refreshed aggregate."""

    child_id: str
    competition: CompetitionDetailView
