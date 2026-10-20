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
    registration_open: bool
    registration_stopped: bool
    registration_opens_at: datetime | None
    registration_closes_at: datetime | None
    #: Whether the organizer keeps a queue for this genre, and whether that queue is
    #: open right now. The wizard needs both: the first explains the badge, the second
    #: decides whether the genre is selectable at all once ``registration_open`` is off.
    waitlist_enabled: bool = False
    waitlist_open: bool = False
    #: Whether the organizer has frozen everything an applicant may change in this
    #: genre. Here rather than on the competition because the freeze is thrown per
    #: genre: вокал is being turned into a programme while хореография still takes
    #: entries, and one flag over both would close the wrong one.
    editing_locked: bool = False


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
    #: ``STANDARD`` or ``MIXED``. A mixed band is deliberately open about who may
    #: enter it, so the wizard asks the applicant what ages the group actually is.
    type: str = "STANDARD"
    #: How the organizer will reduce a mixed group to one age (``AVERAGE`` /
    #: ``OLDEST`` / ``YOUNGEST``); ``None`` for a standard band. Told to the applicant
    #: so what they write is the answer to the question actually being asked.
    mixed_calculation_method: str | None = None


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
    media_mode: str
    #: Whether media is a condition of entry for this format.
    media_required: bool
    #: Only meaningful when ``media_mode`` allows files; sent regardless so the client
    #: never has to guess a limit it would then enforce differently from the server.
    media_allowed_formats: list[str]
    #: The ceiling on the **sum** of the performance's media files.
    media_max_total_size_mb: int
    receipt_required: bool


@dataclass(frozen=True, slots=True)
class RegistrationView:
    competition: RegistrationCompetitionView
    registration_open: bool
    #: Whether at least one genre takes waitlist entries right now. Separate from
    #: ``registration_open`` and not folded into it: the wizard has to stay reachable
    #: when every genre has closed but one keeps a queue, while still saying plainly
    #: that registration is over. One flag cannot do both.
    waitlist_open: bool
    #: Whether one application may hold more than one performance. The wizard offers
    #: no way to add a second when this is false, and the Applications context
    #: refuses one anyway — this is the projection of that same rule, so the button
    #: is absent rather than present and rejected.
    allow_multiple_performances: bool
    #: Whether the wizard asks who the contract is signed with. The Applications
    #: context refuses to accept an order without that name when this is true, so the
    #: card is shown exactly when the name is a condition of submitting.
    collect_payer_details: bool
    #: Whether the wizard offers the free-form note to the organizer. The Applications
    #: context refuses a submission that carries a comment when this is false, so the
    #: field is absent rather than shown and rejected. When true the note stays
    #: optional — it is an opportunity to say something, never a question to answer.
    participant_comment_enabled: bool
    #: Whether each kind of file is admitted by the *calendar* right now: the upload
    #: deadline and a finished festival, resolved into one answer. Projected rather
    #: than derived on the client from ``deadlines`` below, because the client would
    #: be rebuilding a rule the backend already owns — and getting a different answer
    #: the day it mattered.
    #:
    #: The organizer's freeze is deliberately not folded in: it belongs to a genre
    #: (``nominations[].editing_locked``) and these windows belong to the festival, so
    #: the cabinet combines the two for the entry in front of it. See
    #: ``entities/application/lib/file-windows.ts``.
    music_upload_open: bool
    media_upload_open: bool
    document_upload_open: bool
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


#: Consents no festival may waive, projected to the stable codes the Applications
#: context records. ``code`` matches the wizard's ``recordConsents``.
#:
#: These are not settings. A child's data is processed on the basis of the legal
#: representative's consent, and the results of a festival are published on the basis
#: of consent to distribution (LEGAL-001 §4.1, §8.3) — an organizer who could switch
#: either off would be collecting data with nothing behind it. They are therefore
#: always required, whatever the competition's own flags say.
_MANDATORY_CONSENTS: tuple[tuple[str, str], ...] = (
    ("personal_data", "Согласие законного представителя на обработку персональных данных участника"),
    ("distribution", "Согласие на распространение персональных данных (протоколы, программы, документы по итогам)"),
)

#: Consents the competition's settings decide on: needed by some festivals, irrelevant
#: to others, and never a precondition for the platform holding the data at all.
_OPTIONAL_CONSENT_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("media", "Согласие на фото- и видеосъёмку", "require_media_consent"),
    ("regulations", "Принятие положения фестиваля", "require_regulations_acceptance"),
)

#: Offered on every application and required by none: publishing a creative work in the
#: open sections needs its own consent, and withholding it costs the applicant nothing
#: (LEGAL-001 §8.5).
_ELECTIVE_CONSENTS: tuple[tuple[str, str], ...] = (
    (
        "work_publication",
        "Согласие на публикацию творческой работы в открытом доступе",
    ),
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
            registration_open=competition.accepts_submissions_for(category.id, now),
            registration_stopped=category.is_registration_stopped,
            registration_opens_at=category.registration.opens_at,
            registration_closes_at=category.registration.closes_at,
            waitlist_enabled=category.is_waitlist_enabled,
            waitlist_open=competition.accepts_waitlist_for(category.id, now),
            editing_locked=category.is_editing_locked,
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
            type=age.type.value,
            mixed_calculation_method=age.mixed_calculation_method.value if age.mixed_calculation_method is not None else None,
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
        *(RegistrationConsentRequirementView(code=code, label=label, required=True) for code, label in _MANDATORY_CONSENTS),
        *(
            RegistrationConsentRequirementView(code=code, label=label, required=bool(getattr(settings, flag)))
            for code, label, flag in _OPTIONAL_CONSENT_FLAGS
        ),
        *(RegistrationConsentRequirementView(code=code, label=label, required=False) for (code, label) in _ELECTIVE_CONSENTS),
    ]
    upload_requirements = [
        RegistrationUploadRequirementView(
            participation_format_id=requirement.participation_format_id.json(),
            music_required=requirement.music.require_upload,
            music_allowed_formats=list(requirement.music.allowed_formats),
            music_max_upload_size_mb=requirement.music.max_upload_size_mb,
            media_mode=requirement.media.mode.value,
            media_required=requirement.media.require_upload,
            media_allowed_formats=list(requirement.media.allowed_formats),
            media_max_total_size_mb=requirement.media.max_total_size_mb,
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
        waitlist_open=competition.is_any_nomination_waitlisting(now),
        allow_multiple_performances=settings.allow_multiple_performances,
        collect_payer_details=settings.collect_payer_details,
        participant_comment_enabled=settings.participant_comment_enabled,
        music_upload_open=competition.is_music_upload_allowed(now),
        media_upload_open=competition.is_media_upload_allowed(now),
        document_upload_open=competition.is_document_upload_allowed(now),
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
