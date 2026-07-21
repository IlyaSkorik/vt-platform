"""The Registration read model - a single projection for the Registration Wizard.

A **read-only** projection assembled from the Competition Builder's own aggregate:
everything a participant needs to render the registration flow in one shape, so the
frontend never stitches it together from several endpoints. It duplicates no
business rule - admissibility, deadlines and required consents are read straight off
the :class:`~apps.competitions.domain.entities.Competition` aggregate.

Layering: pure and framework-free. It defines the view DTOs and a single
:func:`project_registration` function that maps a ``Competition`` (plus ``now``) to
the projection; the ORM-backed reader that loads the aggregate lives in
``infrastructure/read_models``.

Vocabulary bridge: the Applications context calls the first configuration axis a
*nomination*; the Competition calls it a *category*. This projection presents
categories as **nominations** and keys disciplines/age-categories/participant-groups
to their nomination id, so the wizard's ``setPerformance`` payload maps 1:1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from apps.competitions.domain.entities import Competition

__all__ = [
    "RegistrationAdmissionRuleView",
    "RegistrationAgeCategoryView",
    "RegistrationCompetitionView",
    "RegistrationConsentRequirementView",
    "RegistrationDeadlinesView",
    "RegistrationDisciplineView",
    "RegistrationFormatView",
    "RegistrationNominationView",
    "RegistrationParticipantGroupView",
    "RegistrationServiceView",
    "RegistrationUploadRequirementView",
    "RegistrationView",
    "project_registration",
]


@dataclass(frozen=True, slots=True)
class RegistrationCompetitionView:
    id: str
    title: str
    season: str
    status: str
    venue_name: str | None
    venue_address: str | None


@dataclass(frozen=True, slots=True)
class RegistrationDeadlinesView:
    application: datetime | None
    payment: datetime | None
    music_upload: datetime | None
    document_upload: datetime | None
    correction: datetime | None


@dataclass(frozen=True, slots=True)
class RegistrationNominationView:
    id: str
    name: str
    description: str | None
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegistrationDisciplineView:
    id: str
    nomination_id: str
    name: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegistrationAgeCategoryView:
    id: str
    participant_group_id: str
    name: str
    min_age: int
    max_age: int
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegistrationParticipantGroupView:
    id: str
    name: str
    min_count: int
    max_count: int | None
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegistrationFormatView:
    id: str
    name: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class RegistrationAdmissionRuleView:
    nomination_id: str
    discipline_id: str
    age_category_id: str
    participant_group_id: str
    participation_format_id: str


@dataclass(frozen=True, slots=True)
class RegistrationServiceView:
    id: str
    name: str
    amount: str
    currency: str
    billing_model: str
    required: bool
    available_format_ids: list[str]
    description: str | None


@dataclass(frozen=True, slots=True)
class RegistrationConsentRequirementView:
    code: str
    label: str
    required: bool


@dataclass(frozen=True, slots=True)
class RegistrationUploadRequirementView:
    participation_format_id: str
    music_required: bool
    music_allowed_formats: list[str]
    music_max_upload_size_mb: int
    video_mode: str
    receipt_required: bool


@dataclass(frozen=True, slots=True)
class RegistrationView:
    competition: RegistrationCompetitionView
    registration_open: bool
    deadlines: RegistrationDeadlinesView
    nominations: list[RegistrationNominationView] = field(default_factory=list)
    disciplines: list[RegistrationDisciplineView] = field(default_factory=list)
    age_categories: list[RegistrationAgeCategoryView] = field(default_factory=list)
    participant_groups: list[RegistrationParticipantGroupView] = field(default_factory=list)
    participation_formats: list[RegistrationFormatView] = field(default_factory=list)
    admission_rules: list[RegistrationAdmissionRuleView] = field(default_factory=list)
    additional_services: list[RegistrationServiceView] = field(default_factory=list)
    required_consents: list[RegistrationConsentRequirementView] = field(default_factory=list)
    upload_requirements: list[RegistrationUploadRequirementView] = field(default_factory=list)


#: The consent flags the Competition settings expose, projected to stable codes the
#: Applications context records. ``code`` matches the wizard's ``recordConsents``.
_CONSENT_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("personal_data", "Согласие на обработку персональных данных", "require_personal_data_consent"),
    ("media", "Согласие на фото- и видеосъёмку", "require_media_consent"),
    ("regulations", "Принятие положения фестиваля", "require_regulations_acceptance"),
)


def project_registration(competition: Competition, *, now: datetime) -> RegistrationView:
    """Project a ``Competition`` aggregate into the single Registration view."""
    settings = competition.settings
    venue = competition.venue

    nominations = [
        RegistrationNominationView(
            id=category.id.json(),
            name=category.name.value,
            description=category.description.value if category.description is not None else None,
            sort_order=category.sort_order,
        )
        for category in competition.categories
    ]
    disciplines = [
        RegistrationDisciplineView(
            id=discipline.id.json(),
            nomination_id=discipline.category_id.json(),
            name=discipline.name.value,
            sort_order=discipline.sort_order,
        )
        for discipline in competition.disciplines
    ]
    age_categories = [
        RegistrationAgeCategoryView(
            id=age.id.json(),
            participant_group_id=age.participant_group_id.json(),
            name=age.name.value,
            min_age=age.age_range.min_age,
            max_age=age.age_range.max_age,
            sort_order=age.sort_order,
        )
        for age in competition.age_categories
    ]
    participant_groups = [
        RegistrationParticipantGroupView(
            id=group.id.json(),
            name=group.name.value,
            min_count=group.count_range.min_count,
            max_count=group.count_range.max_count,
            sort_order=group.sort_order,
        )
        for group in competition.participant_groups
    ]
    formats = [
        RegistrationFormatView(id=fmt.id.json(), name=fmt.name.value, sort_order=fmt.sort_order)
        for fmt in competition.participation_formats
        if fmt.enabled
    ]
    admission_rules = [
        RegistrationAdmissionRuleView(
            nomination_id=rule.combination.category_id.json(),
            discipline_id=rule.combination.discipline_id.json(),
            age_category_id=rule.combination.age_category_id.json(),
            participant_group_id=rule.combination.participant_group_id.json(),
            participation_format_id=rule.combination.participation_format_id.json(),
        )
        for rule in competition.admission_rules
    ]
    services = [
        RegistrationServiceView(
            id=service.id.json(),
            name=service.name.value,
            amount=str(service.price.amount),
            currency=service.price.currency.value,
            billing_model=service.billing_model.value,
            required=service.required,
            available_format_ids=[fmt.json() for fmt in service.available_format_ids],
            description=service.description.value if service.description is not None else None,
        )
        for service in competition.additional_services
        if service.is_enabled
    ]
    required_consents = [
        RegistrationConsentRequirementView(code=code, label=label, required=bool(getattr(settings, flag))) for code, label, flag in _CONSENT_FLAGS
    ]
    upload_requirements = [
        RegistrationUploadRequirementView(
            participation_format_id=requirement.participation_format_id.json(),
            music_required=requirement.music.require_upload,
            music_allowed_formats=list(requirement.music.allowed_formats),
            music_max_upload_size_mb=requirement.music.max_upload_size_mb,
            video_mode=requirement.video.mode.value,
            receipt_required=requirement.payment_receipt.require_receipt,
        )
        for requirement in settings.format_requirements
    ]

    return RegistrationView(
        competition=RegistrationCompetitionView(
            id=competition.id.json(),
            title=competition.title.value,
            season=competition.season.value,
            status=competition.status.value,
            venue_name=venue.name if venue is not None else None,
            venue_address=venue.address if venue is not None else None,
        ),
        registration_open=competition.is_application_allowed(now),
        deadlines=RegistrationDeadlinesView(
            application=competition.deadlines.application,
            payment=competition.deadlines.payment,
            music_upload=competition.deadlines.music_upload,
            document_upload=competition.deadlines.document_upload,
            correction=competition.deadlines.correction,
        ),
        nominations=nominations,
        disciplines=disciplines,
        age_categories=age_categories,
        participant_groups=participant_groups,
        participation_formats=formats,
        admission_rules=admission_rules,
        additional_services=services,
        required_consents=required_consents,
        upload_requirements=upload_requirements,
    )
