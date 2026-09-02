"""The operator's eraser: removing a festival, an order or an account for good.

Why it lives here rather than in one of the domains: erasing a festival touches
Competitions, Applications, Diplomas, Programs and Results at once, and no single
one of those contexts may own the others. That is the same pragmatic seam
:mod:`read_models` and :mod:`loadtest` document — a tool that spans several
contexts, kept where its coupling is visible instead of smuggled into a domain
that would then have to know about all of them.

**This is a hard delete, and it is not recoverable.** Everywhere else the platform
soft-deletes: a row keeps a ``deleted_at`` and the history survives. That is the
right default for a business record, and the wrong one for the two jobs this
module exists to do — freeing the disk a cancelled festival's diplomas sit on, and
answering "remove my data" with something more than a hidden row.

Three properties keep that safe to expose:

* **Nothing runs unseen.** :func:`plan` reports every table and every file that
  would go, and the console shows it before the button does anything. The same
  plan is what :func:`purge` then executes, so the numbers the operator agreed to
  are the numbers that get deleted.
* **The name has to be typed.** :func:`purge` refuses unless ``confirm`` matches
  the target's own label. An id alone is not enough — the caller has to have read
  the thing first, which is exactly the step a mis-click skips.
* **Rows first, then files.** The inverse of :func:`loadtest.cleanup`, and
  deliberately so: that data was synthetic, this is not. A crash between the two
  halves leaves unreferenced files in storage, which costs disk; the other order
  would leave live rows pointing at bytes that no longer exist.

The blast radius of each target is spelled out on :func:`_scope`. The short
version: every target takes everything held *inside* it and nothing above it — a
festival leaves the organization, its staff and its diploma templates standing, and
the two narrow targets go further down still. A programme is one arrangement of the
acts, so erasing it leaves the acts; a template is a design, so erasing it leaves the
documents already issued from it. Both exist because the whole festival is far too
blunt an answer to "программу собрали не так" or "шаблон сверстали заново".
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count

from apps.applications.infrastructure.models import ApplicationModel, ApplicationRevisionModel, SubmissionModel
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
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    DiplomaModel,
    DocumentTypeChoices,
    GenerationRunModel,
    IssuedDocumentModel,
    PrintJobModel,
    TemplateDocumentModel,
    TemplateFieldModel,
    TemplateModel,
)
from apps.diplomas.infrastructure.pdf.workspace import storage_key_of
from apps.identity.infrastructure.models import UserModel
from apps.notifications.infrastructure.models import NotificationModel
from apps.organization.infrastructure.models import (
    MembershipStatusChoices,
    OrganizationModel,
    StaffInvitationModel,
    StaffMembershipModel,
    StaffRoleChoices,
)
from apps.participants.infrastructure.models import (
    EducationalOrganizationModel,
    GuardianLinkModel,
    ParticipantModel,
    ParticipantRegistryModel,
)
from apps.platform.infrastructure.models import PlatformAdministratorModel
from apps.programs.infrastructure.models import ProgramColumnModel, ProgramItemModel, ProgramModel, ProgramShareModel
from apps.results.infrastructure.models import ProtocolModel, ProtocolRowModel
from apps.teachers.infrastructure.models import TeacherModel

__all__ = [
    "TARGETS",
    "ConfirmationMismatchError",
    "Plan",
    "PurgeError",
    "SelfDeletionError",
    "Target",
    "TargetNotFoundError",
    "UnknownTargetError",
    "plan",
    "purge",
    "search",
]

#: The things the console can erase, in the order it offers them. Keys are part of
#: the URL, so they are English and stable; the labels are what the operator reads.
TARGETS: dict[str, str] = {
    "festival": "Фестиваль",
    "program": "Программа фестиваля",
    "application": "Заявка",
    "organization": "Организация",
    "template": "Шаблон диплома",
    "account": "Аккаунт",
    "participant": "Участник реестра",
    "teacher": "Педагог реестра",
}

#: The most candidates a search hands back. A search is a way to find one known
#: thing, not a way to browse the database — a longer list would invite picking by
#: position rather than by reading, which is the one habit this screen must not build.
SEARCH_LIMIT = 20


class PurgeError(Exception):
    """Base class for every refusal in this module."""


class UnknownTargetError(PurgeError):
    """The target kind is not one of :data:`TARGETS`."""


class TargetNotFoundError(PurgeError):
    """No such object — already gone, or never existed."""


class ConfirmationMismatchError(PurgeError):
    """``confirm`` did not match the target's label, so nothing was touched."""


class SelfDeletionError(PurgeError):
    """The operator aimed the eraser at their own account."""


@dataclass(frozen=True, slots=True)
class Target:
    """What is about to be erased, as the console names it."""

    kind: str
    id: str
    #: The string the operator has to type to confirm — a title, a name, an email.
    label: str
    #: The second line that tells two similarly named rows apart.
    hint: str


@dataclass(frozen=True, slots=True)
class Row:
    """One table's contribution to the plan."""

    table: str
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class Plan:
    """Everything :func:`purge` would delete, before it deletes any of it."""

    target: Target
    rows: tuple[Row, ...]
    files: int
    #: Consequences worth reading twice, in the operator's language.
    warnings: tuple[str, ...]

    @property
    def total(self) -> int:
        return sum(row.count for row in self.rows)


@dataclass(slots=True)
class _Scope:
    """The id sets a target expands into — the whole blast radius, resolved once.

    Both halves of the operation read this and nothing else: the plan counts over
    it, the delete runs over it. One resolution means the preview cannot describe a
    different set of rows than the one that gets erased.
    """

    target: Target
    competition_ids: list[uuid.UUID] = field(default_factory=list)
    application_ids: list[uuid.UUID] = field(default_factory=list)
    submission_ids: list[uuid.UUID] = field(default_factory=list)
    program_ids: list[uuid.UUID] = field(default_factory=list)
    template_ids: list[uuid.UUID] = field(default_factory=list)
    organization_ids: list[uuid.UUID] = field(default_factory=list)
    user_ids: list[uuid.UUID] = field(default_factory=list)
    registry_ids: list[uuid.UUID] = field(default_factory=list)
    teacher_ids: list[uuid.UUID] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Public entry points
# ----------------------------------------------------------------------


def plan(kind: str, object_id: str) -> Plan:
    """What erasing this target would take with it. Reads only; changes nothing."""
    return _render(_scope(kind, object_id))


def purge(kind: str, object_id: str, *, confirm: str, actor_id: uuid.UUID | None = None) -> Plan:
    """Erase the target. Returns what actually went, counted before deletion.

    ``confirm`` must equal the target's label (case and surrounding whitespace are
    forgiven, nothing else is). The returned plan is the pre-delete count, which is
    what the operator's confirmation was given against — reading it back afterwards
    would report zeros.
    """
    scope = _scope(kind, object_id)
    if _normalise(confirm) != _normalise(scope.target.label):
        raise ConfirmationMismatchError(f"Подтверждение не совпадает с названием: ожидается «{scope.target.label}».")
    if actor_id is not None and actor_id in scope.user_ids:
        raise SelfDeletionError("Нельзя удалить аккаунт, из которого вы сейчас работаете.")

    references = _files(scope)
    rendered = _render(scope, references)
    with transaction.atomic():
        _delete(scope)
    # Outside the transaction, and after it: storage is not transactional, so a
    # rollback could not put these back. Orphaned bytes cost disk; a live row
    # pointing at bytes that are gone costs a broken download for a participant.
    _drop_files(references)
    return rendered


def search(kind: str, query: str) -> list[Target]:
    """Candidates matching ``query`` — an id, a name, or an email."""
    text = query.strip()
    if kind not in TARGETS:
        raise UnknownTargetError(f"Unknown purge target {kind!r}.")
    if not text:
        return []
    return _SEARCH[kind](text)


# ----------------------------------------------------------------------
# Resolving a target into its blast radius
# ----------------------------------------------------------------------


def _scope(kind: str, object_id: str) -> _Scope:
    """Expand one id into every id set that hangs off it.

    Each branch below is a deliberate statement about how far down the tree the
    deletion reaches — and, just as importantly, where it stops.
    """
    if kind not in TARGETS:
        raise UnknownTargetError(f"Unknown purge target {kind!r}.")
    identifier = _as_uuid(object_id)
    return _SCOPES[kind](identifier)


def _festival_scope(competition_id: uuid.UUID) -> _Scope:
    """A festival takes everything held inside it and nothing above it.

    Its orders, performances, programs, protocols and diplomas go. The organization
    that ran it, that organization's staff, and its diploma templates stay: those
    outlive any single festival and are used by the next one.
    """
    competition = CompetitionModel.objects.filter(id=competition_id).first()
    if competition is None:
        raise TargetNotFoundError("Фестиваль не найден.")
    organization_name = _organization_names([competition.organizer_id]).get(competition.organizer_id, "—")
    scope = _Scope(
        target=Target(
            kind="festival",
            id=str(competition.id),
            label=competition.title,
            hint=f"{organization_name} · {competition.season}",
        ),
        competition_ids=[competition.id],
    )
    scope.application_ids = _ids(ApplicationModel.objects.filter(competition_id=competition.id))
    scope.submission_ids = _ids(SubmissionModel.objects.filter(competition_id=competition.id))
    scope.program_ids = _ids(ProgramModel.objects.filter(competition_id=competition.id))
    scope.warnings.append("Организация, её сотрудники и шаблоны дипломов остаются — удаляется только фестиваль.")
    if DiplomaModel.objects.filter(competition_id=competition.id).exists():
        scope.warnings.append("У фестиваля есть выданные дипломы: их номера и ссылки проверки перестанут открываться навсегда.")
    return scope


def _program_scope(program_id: uuid.UUID) -> _Scope:
    """One programme of a festival: its running order, its columns, its public links.

    The narrowest festival-shaped target there is, and deliberately so. A programme
    is one *arrangement* of the acts, not the acts themselves — so the orders, the
    performances, the diplomas and the protocols all stay, and what goes is the
    schedule built over them. That is what "программу собрали не так, соберём
    заново" asks for, and erasing the festival to get it would be absurd.
    """
    program = ProgramModel.objects.filter(id=program_id).first()
    if program is None:
        raise TargetNotFoundError("Программа не найдена.")
    competition = CompetitionModel.objects.filter(id=program.competition_id).first()
    items = ProgramItemModel.objects.filter(program_id=program.id).count()
    scope = _Scope(
        target=Target(
            kind="program",
            id=str(program.id),
            label=program.name,
            hint=f"{competition.title if competition is not None else '—'} · номеров: {items}",
        ),
        program_ids=[program.id],
    )
    scope.warnings.append("Фестиваль, его заявки, выступления и протоколы остаются — удаляется только эта программа.")
    if ProgramItemModel.objects.filter(program_id=program.id, number__gt=0).exists():
        # ``numbers_issued`` lives on the programme row and goes with it, so the
        # numbers participants were already told are not recoverable by rebuilding.
        scope.warnings.append("Выданные номера участников уйдут вместе с программой — собранная заново программа начнёт нумерацию с единицы.")
    if (shares := ProgramShareModel.objects.filter(program_id=program.id).count()) > 0:
        scope.warnings.append(f"Публичные ссылки на эту программу ({shares}) перестанут открываться навсегда.")
    return scope


def _application_scope(application_id: uuid.UUID) -> _Scope:
    """One order, with the performances it was placed for.

    The festival keeps its taxonomy, programs and protocols; only the rows that
    named *these* performances are pulled out of them, so a running order does not
    keep a slot for a performance that no longer exists.
    """
    application = ApplicationModel.objects.filter(id=application_id).first()
    if application is None:
        raise TargetNotFoundError("Заявка не найдена.")
    applicant = UserModel.objects.filter(id=application.applicant_id).first()
    competition = CompetitionModel.objects.filter(id=application.competition_id).first()
    label = applicant.email if applicant is not None else str(application.id)
    scope = _Scope(
        target=Target(
            kind="application",
            id=str(application.id),
            label=label,
            hint=f"{competition.title if competition is not None else '—'} · {application.status}",
        ),
        application_ids=[application.id],
    )
    # The order's own list of performances, not "everything this applicant sent to
    # this festival": a second order from the same person must not be caught here.
    referenced = {
        parsed for row in application.submission_refs or [] if (parsed := _maybe_uuid(str((row or {}).get("submission_id") or ""))) is not None
    }
    scope.submission_ids = _ids(SubmissionModel.objects.filter(id__in=referenced))
    scope.warnings.append("Фестиваль и его настройки не затрагиваются — удаляется только эта заявка.")
    if ProgramItemModel.objects.filter(submission_id__in=scope.submission_ids).exists():
        scope.warnings.append("Номера этой заявки исчезнут из программы — нумерация соседних номеров не сдвинется.")
    return scope


def _organization_scope(organization_id: uuid.UUID) -> _Scope:
    """An organization, every festival it ever ran, and its own diploma templates.

    The accounts of its staff stay: a person is not owned by the organization they
    work for, and the same account may hold a membership in another one.
    """
    organization = OrganizationModel.objects.filter(id=organization_id).first()
    if organization is None:
        raise TargetNotFoundError("Организация не найдена.")
    scope = _Scope(
        target=Target(
            kind="organization",
            id=str(organization.id),
            label=organization.name,
            hint=f"/{organization.slug} · {organization.status}",
        ),
        organization_ids=[organization.id],
    )
    scope.competition_ids = _ids(CompetitionModel.objects.filter(organizer_id=organization.id))
    scope.application_ids = _ids(ApplicationModel.objects.filter(competition_id__in=scope.competition_ids))
    scope.submission_ids = _ids(SubmissionModel.objects.filter(competition_id__in=scope.competition_ids))
    scope.program_ids = _ids(ProgramModel.objects.filter(competition_id__in=scope.competition_ids))
    scope.template_ids = _ids(TemplateModel.objects.filter(organizer_id=organization.id))
    scope.warnings.append("Аккаунты сотрудников остаются — снимаются только их роли в этой организации.")
    if scope.competition_ids:
        scope.warnings.append(f"Вместе с организацией удаляются все её фестивали ({len(scope.competition_ids)}) целиком.")
    return scope


def _template_scope(template_id: uuid.UUID) -> _Scope:
    """One diploma template: its layout, its uploaded blanks, its bindings.

    Diplomas already issued from it stay, and keep working. Each one carries its own
    snapshot of the template and its own rendered PDF, so a printed diploma and the
    link that verifies it do not depend on the layout still existing. What is lost
    is the ability to produce any more from this design.
    """
    template = TemplateModel.objects.filter(id=template_id).first()
    if template is None:
        raise TargetNotFoundError("Шаблон не найден.")
    organization_name = _organization_names([template.organizer_id]).get(template.organizer_id, "—")
    scope = _Scope(
        target=Target(
            kind="template",
            id=str(template.id),
            label=template.name,
            hint=f"{organization_name} · {_document_type_label(template.type)}",
        ),
        template_ids=[template.id],
    )
    scope.warnings.append("Организация, её фестивали и уже выданные документы остаются — удаляется только сам шаблон.")
    if (assignments := AssignmentModel.objects.filter(template_id=template.id).count()) > 0:
        scope.warnings.append(
            f"Шаблон привязан к номинациям ({assignments}): привязки снимутся, и генерация в них остановится, пока не выбран другой шаблон."
        )
    if (issued := DiplomaModel.objects.filter(template_id=template.id).count()) > 0:
        scope.warnings.append(
            f"По этому шаблону уже выдано документов: {issued}. Они продолжат открываться, но перевыпустить их по этому макету будет нельзя."
        )
    return scope


def _account_scope(user_id: uuid.UUID) -> _Scope:
    """One person's account and everything entered under it.

    Their orders and performances, their registry of participants and schools,
    their teachers, their notifications, their sessions and consents, and any
    platform-administrator grant they hold. Festivals they ran as staff belong to
    the organization, not to them, and stay.
    """
    user = UserModel.objects.filter(id=user_id).first()
    if user is None:
        raise TargetNotFoundError("Аккаунт не найден.")
    scope = _Scope(
        target=Target(
            kind="account",
            id=str(user.id),
            label=user.email,
            hint=" ".join(part for part in (user.last_name, user.first_name) if part) or "—",
        ),
        user_ids=[user.id],
    )
    scope.application_ids = _ids(ApplicationModel.objects.filter(applicant_id=user.id))
    scope.submission_ids = _ids(SubmissionModel.objects.filter(applicant_id=user.id))
    scope.registry_ids = _ids(ParticipantRegistryModel.objects.filter(owner_id=user.id))
    scope.teacher_ids = _ids(TeacherModel.objects.filter(owner_id=user.id))
    scope.warnings.append("Фестивали организаций, где этот человек в штате, остаются — снимается только его доступ.")
    for name in _sole_owner_of(user.id):
        scope.warnings.append(f"Это единственный действующий владелец организации «{name}» — она останется без владельца.")
    return scope


def _participant_scope(participant_id: uuid.UUID) -> _Scope:
    """One registry card, and the schools it was linked to.

    Performances already sent carry their own copy of the name and birth date —
    that copy is the record of what was submitted, and it stays.
    """
    participant = ParticipantRegistryModel.objects.filter(id=participant_id).first()
    if participant is None:
        raise TargetNotFoundError("Участник не найден.")
    owner = UserModel.objects.filter(id=participant.owner_id).first()
    label = participant.collective_name or " ".join(part for part in (participant.last_name, participant.first_name) if part)
    scope = _Scope(
        target=Target(
            kind="participant",
            id=str(participant.id),
            label=label or str(participant.id),
            hint=f"{owner.email if owner is not None else '—'} · {participant.birth_date:%d.%m.%Y}",
        ),
        registry_ids=[participant.id],
    )
    scope.warnings.append("В уже поданных заявках имя останется — это снимок того, что было заявлено.")
    return scope


def _teacher_scope(teacher_id: uuid.UUID) -> _Scope:
    """One teacher card. Credits inside sent performances are a snapshot and stay."""
    teacher = TeacherModel.objects.filter(id=teacher_id).first()
    if teacher is None:
        raise TargetNotFoundError("Педагог не найден.")
    owner = UserModel.objects.filter(id=teacher.owner_id).first()
    label = " ".join(part for part in (teacher.last_name, teacher.first_name) if part)
    scope = _Scope(
        target=Target(
            kind="teacher",
            id=str(teacher.id),
            label=label or str(teacher.id),
            hint=f"{owner.email if owner is not None else '—'} · {teacher.role}",
        ),
        teacher_ids=[teacher.id],
    )
    scope.warnings.append("В уже поданных заявках педагог останется указан — это снимок того, что было заявлено.")
    return scope


_SCOPES: dict[str, Callable[[uuid.UUID], _Scope]] = {
    "festival": _festival_scope,
    "program": _program_scope,
    "application": _application_scope,
    "organization": _organization_scope,
    "template": _template_scope,
    "account": _account_scope,
    "participant": _participant_scope,
    "teacher": _teacher_scope,
}


# ----------------------------------------------------------------------
# Counting, and then deleting, one resolved scope
# ----------------------------------------------------------------------


def _querysets(scope: _Scope) -> Iterator[tuple[str, str, Any]]:
    """Every table the scope reaches, paired with the rows it reaches in it.

    Yielded in the order the delete runs: children before the parents whose cascade
    would otherwise take them, and the two aggregates people care about last, so a
    partial failure leaves the recognisable row rather than an orphaned tail.

    Rows that cascade from a parent in this same list are still named here — the
    plan has to be able to say "48 номинаций", and counting is what the preview is
    for. Deleting them twice is free; not showing them is not.
    """
    competitions = scope.competition_ids
    applications = scope.application_ids
    submissions = scope.submission_ids
    programs = scope.program_ids
    templates = scope.template_ids
    organizations = scope.organization_ids
    users = scope.user_ids

    if competitions:
        yield "competitions_category", "Номинации", CategoryModel.objects.filter(competition_id__in=competitions)
        yield "competitions_discipline", "Дисциплины", DisciplineModel.objects.filter(competition_id__in=competitions)
        yield "competitions_age_category", "Возрастные категории", AgeCategoryModel.objects.filter(competition_id__in=competitions)
        yield "competitions_participant_group", "Составы", ParticipantGroupModel.objects.filter(competition_id__in=competitions)
        yield "competitions_participation_format", "Форматы участия", ParticipationFormatModel.objects.filter(competition_id__in=competitions)
        yield "competitions_admission_rule", "Правила допуска", AdmissionRuleModel.objects.filter(competition_id__in=competitions)
        yield "competitions_pricing_rule", "Правила цен", PricingRuleModel.objects.filter(competition_id__in=competitions)
        yield "competitions_additional_service", "Доп. услуги", AdditionalServiceModel.objects.filter(competition_id__in=competitions)
        yield "competitions_contact", "Контакты", ContactModel.objects.filter(competition_id__in=competitions)
        yield "competitions_information_block", "Информационные блоки", InformationBlockModel.objects.filter(competition_id__in=competitions)
        yield "competitions_regulation", "Положения", RegulationModel.objects.filter(competition_id__in=competitions)
        yield "competitions_document", "Документы", DocumentModel.objects.filter(competition_id__in=competitions)

    yield "diplomas_diploma", "Дипломы", _by_competition_or_submission(DiplomaModel, competitions, submissions)
    yield "diplomas_issued_document", "Выданные документы", _by_competition_or_submission(IssuedDocumentModel, competitions, submissions)
    if competitions or templates:
        # Before the templates below, and by template as well as by festival: the
        # assignment's FK is PROTECT, so a template with any binding left standing
        # refuses to go, and a template's binding may sit on a festival that is not
        # itself in this scope.
        yield "diplomas_assignment", "Привязки шаблонов", _assignments(competitions, templates)
    if competitions:
        yield "diplomas_print_job", "Задачи печати", PrintJobModel.objects.filter(competition_id__in=competitions)
        yield "diplomas_generation_run", "Прогоны генерации", GenerationRunModel.objects.filter(competition_id__in=competitions)
    if templates:
        yield "diplomas_template_field", "Поля шаблонов", TemplateFieldModel.objects.filter(template_id__in=templates)
        yield "diplomas_template_document", "Загруженные бланки", TemplateDocumentModel.objects.filter(template_id__in=templates)
        yield "diplomas_template", "Шаблоны дипломов", TemplateModel.objects.filter(id__in=templates)

    if programs:
        yield "programs_program_column", "Колонки программ", ProgramColumnModel.objects.filter(program_id__in=programs)
        yield "programs_program_share", "Публичные страницы программ", ProgramShareModel.objects.filter(program_id__in=programs)
        yield "programs_program_item", "Номера в программах", ProgramItemModel.objects.filter(program_id__in=programs)
        yield "programs_program", "Программы", ProgramModel.objects.filter(id__in=programs)
    elif submissions:
        # The festival stays, so its programmes keep standing — only the lines that
        # named these performances come out of them.
        yield "programs_program_item", "Номера в программах", ProgramItemModel.objects.filter(submission_id__in=submissions)

    if competitions:
        yield "results_protocol", "Протоколы", ProtocolModel.objects.filter(competition_id__in=competitions)
    elif submissions:
        yield "results_protocol_row", "Строки протоколов", ProtocolRowModel.objects.filter(submission_id__in=submissions)

    yield "applications_application_revision", "История изменений заявок", _revisions(competitions, applications)
    if submissions:
        yield "applications_submission", "Номера (выступления)", SubmissionModel.objects.filter(id__in=submissions)
    if applications:
        yield "applications_application", "Заявки", ApplicationModel.objects.filter(id__in=applications)

    if users:
        yield "notifications_notification", "Уведомления", NotificationModel.objects.filter(recipient_id__in=users)
        yield "participants_guardian_link", "Связи с представителями", GuardianLinkModel.objects.filter(guardian_id__in=users)
        yield "participants_participant", "Защищённые профили участников", ParticipantModel.objects.filter(created_by_id__in=users)
        yield "participants_educational_organization", "Учебные заведения в реестре", EducationalOrganizationModel.objects.filter(owner_id__in=users)
        yield "platform_administrator", "Права администратора платформы", PlatformAdministratorModel.objects.filter(user_id__in=users)

    if scope.registry_ids or users:
        yield "participants_registry", "Участники в реестре", _owned(ParticipantRegistryModel, scope.registry_ids, users)
    if scope.teacher_ids or users:
        yield "teachers_teacher", "Педагоги в реестре", _owned(TeacherModel, scope.teacher_ids, users)

    if organizations or users:
        yield "organization_staff_membership", "Роли сотрудников", _memberships(organizations, users)
    if organizations:
        yield "organization_staff_invitation", "Приглашения сотрудников", StaffInvitationModel.objects.filter(organization_id__in=organizations)

    if competitions:
        yield "competitions_competition", "Фестивали", CompetitionModel.objects.filter(id__in=competitions)
    if organizations:
        yield "organization_organization", "Организации", OrganizationModel.objects.filter(id__in=organizations)
    if users:
        yield "identity_user", "Аккаунты", UserModel.objects.filter(id__in=users)


def _render(scope: _Scope, references: tuple[str, ...] | None = None) -> Plan:
    """Count the scope without touching it.

    ``references`` is passed by :func:`purge`, which has already collected them and
    would otherwise pay for the same dozen queries twice.
    """
    rows = tuple(Row(table=table, label=label, count=queryset.count()) for table, label, queryset in _querysets(scope))
    return Plan(
        target=scope.target,
        rows=tuple(row for row in rows if row.count),
        files=len(_files(scope) if references is None else references),
        warnings=tuple(scope.warnings),
    )


def _delete(scope: _Scope) -> None:
    """Run the deletion. Must be called inside a transaction."""
    for _table, _label, queryset in _querysets(scope):
        queryset.delete()


def _by_competition_or_submission(model: Any, competitions: list[uuid.UUID], submissions: list[uuid.UUID]) -> Any:
    """Diplomas reachable either through the festival or through the performance.

    Both columns are needed: erasing a festival must take diplomas whose performance
    row is already gone, and erasing a single order must take that order's diplomas
    while the festival's others stay.
    """
    queryset = model.objects.none()
    if competitions:
        queryset = queryset | model.objects.filter(competition_id__in=competitions)
    if submissions:
        queryset = queryset | model.objects.filter(submission_id__in=submissions)
    return queryset


def _assignments(competitions: list[uuid.UUID], templates: list[uuid.UUID]) -> Any:
    """Template bindings reachable through a festival or through the template itself."""
    queryset = AssignmentModel.objects.none()
    if competitions:
        queryset = queryset | AssignmentModel.objects.filter(competition_id__in=competitions)
    if templates:
        queryset = queryset | AssignmentModel.objects.filter(template_id__in=templates)
    return queryset


def _revisions(competitions: list[uuid.UUID], applications: list[uuid.UUID]) -> Any:
    queryset = ApplicationRevisionModel.objects.none()
    if competitions:
        queryset = queryset | ApplicationRevisionModel.objects.filter(competition_id__in=competitions)
    if applications:
        queryset = queryset | ApplicationRevisionModel.objects.filter(application_id__in=applications)
    return queryset


def _owned(model: Any, own_ids: list[uuid.UUID], owner_ids: list[uuid.UUID]) -> Any:
    """A registry row picked by its own id, or every row belonging to an owner."""
    queryset = model.objects.none()
    if own_ids:
        queryset = queryset | model.objects.filter(id__in=own_ids)
    if owner_ids:
        queryset = queryset | model.objects.filter(owner_id__in=owner_ids)
    return queryset


def _memberships(organizations: list[uuid.UUID], users: list[uuid.UUID]) -> Any:
    queryset = StaffMembershipModel.objects.none()
    if organizations:
        queryset = queryset | StaffMembershipModel.objects.filter(organization_id__in=organizations)
    if users:
        queryset = queryset | StaffMembershipModel.objects.filter(user_id__in=users)
    return queryset


# ----------------------------------------------------------------------
# Files
# ----------------------------------------------------------------------


def _files(scope: _Scope) -> tuple[str, ...]:
    """Every stored reference the scope reaches, deduplicated.

    Read while the rows are still there — the references live *on* the rows, so
    after the delete there is no way left to find the bytes they point at.
    """
    references: list[str] = []
    competitions = scope.competition_ids
    submissions = scope.submission_ids
    applications = scope.application_ids

    if competitions:
        for logo, banner, poster in CompetitionModel.objects.filter(id__in=competitions).values_list("logo", "banner", "poster"):
            references += [logo or "", banner or "", poster or ""]
        references += list(RegulationModel.objects.filter(competition_id__in=competitions).values_list("file_reference", flat=True))
        references += list(DocumentModel.objects.filter(competition_id__in=competitions).values_list("file_reference", flat=True))

    if submissions:
        for attachments in SubmissionModel.objects.filter(id__in=submissions).values_list("attachments", flat=True):
            references += [str((row or {}).get("file") or "") for row in attachments or []]
    if applications:
        for receipts in ApplicationModel.objects.filter(id__in=applications).values_list("payment_receipts", flat=True):
            references += [str((row or {}).get("file_reference") or "") for row in receipts or []]

    diplomas = _by_competition_or_submission(DiplomaModel, competitions, submissions)
    references += list(diplomas.values_list("print_pdf_path", flat=True))
    references += list(diplomas.values_list("official_pdf_path", flat=True))
    references += list(_by_competition_or_submission(IssuedDocumentModel, competitions, submissions).values_list("pdf_path", flat=True))
    if competitions:
        references += list(PrintJobModel.objects.filter(competition_id__in=competitions).values_list("zip_path", flat=True))
        references += list(GenerationRunModel.objects.filter(competition_id__in=competitions).values_list("zip_path", flat=True))

    if scope.template_ids:
        references += list(TemplateDocumentModel.objects.filter(template_id__in=scope.template_ids).values_list("file_reference", flat=True))

    if scope.registry_ids or scope.user_ids:
        references += list(_owned(ParticipantRegistryModel, scope.registry_ids, scope.user_ids).values_list("avatar_url", flat=True))

    return tuple(dict.fromkeys(reference for reference in references if (reference or "").strip()))


def _drop_files(references: Iterable[str]) -> None:
    """Remove the bytes. One failure must not strand the rest of the batch."""
    for reference in references:
        key = storage_key_of(reference)
        try:
            if default_storage.exists(key):
                default_storage.delete(key)
        except OSError:
            # Nothing to do about it here, and nothing that should stop the sweep:
            # the row is already gone, so the file is unreachable either way.
            continue


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------


def _festival_candidates(query: str) -> list[Target]:
    matches = CompetitionModel.objects.filter(title__icontains=query)
    if (identifier := _maybe_uuid(query)) is not None:
        matches = CompetitionModel.objects.filter(id=identifier)
    rows = list(matches.order_by("-created_at")[:SEARCH_LIMIT])
    names = _organization_names([row.organizer_id for row in rows])
    return [Target(kind="festival", id=str(row.id), label=row.title, hint=f"{names.get(row.organizer_id, '—')} · {row.season}") for row in rows]


def _program_candidates(query: str) -> list[Target]:
    """Programmes are found by their own name, by their festival's, or by id.

    Both handles, because one of them is usually useless: a programme is called
    "День первый", which names nothing on its own, and the operator arrives holding
    the festival instead. Matching the festival's title lists its programmes and
    lets the operator pick the day.
    """
    if (identifier := _maybe_uuid(query)) is not None:
        matches = ProgramModel.objects.filter(id=identifier)
    else:
        competition_ids = list(CompetitionModel.objects.filter(title__icontains=query).values_list("id", flat=True)[:SEARCH_LIMIT])
        matches = ProgramModel.objects.filter(name__icontains=query) | ProgramModel.objects.filter(competition_id__in=competition_ids)
    rows = list(matches.order_by("name")[:SEARCH_LIMIT])
    titles = dict(CompetitionModel.objects.filter(id__in=[row.competition_id for row in rows]).values_list("id", "title"))
    counts = _item_counts([row.id for row in rows])
    return [
        Target(
            kind="program",
            id=str(row.id),
            label=row.name,
            hint=f"{titles.get(row.competition_id, '—')} · номеров: {counts.get(row.id, 0)}",
        )
        for row in rows
    ]


def _template_candidates(query: str) -> list[Target]:
    """Templates are found by their own name, by their organization's, or by id.

    Same reasoning as programmes: half the libraries on the platform hold a template
    called "Диплом", so the organization has to be a handle too — and the hint has
    to carry it, because the name alone cannot tell two of them apart.
    """
    if (identifier := _maybe_uuid(query)) is not None:
        matches = TemplateModel.objects.filter(id=identifier)
    else:
        organization_ids = list(OrganizationModel.objects.filter(name__icontains=query).values_list("id", flat=True)[:SEARCH_LIMIT])
        matches = TemplateModel.objects.filter(name__icontains=query) | TemplateModel.objects.filter(organizer_id__in=organization_ids)
    rows = list(matches.order_by("name")[:SEARCH_LIMIT])
    names = _organization_names([row.organizer_id for row in rows])
    return [
        Target(
            kind="template",
            id=str(row.id),
            label=row.name,
            hint=f"{names.get(row.organizer_id, '—')} · {_document_type_label(row.type)}",
        )
        for row in rows
    ]


def _application_candidates(query: str) -> list[Target]:
    """Orders are found by their applicant's email, or by their own id.

    An order has no name of its own, and a status is not a handle — the person who
    placed it is how a support request names it in the first place.
    """
    if (identifier := _maybe_uuid(query)) is not None:
        matches = ApplicationModel.objects.filter(id=identifier)
    else:
        applicant_ids = list(UserModel.objects.filter(email__icontains=query).values_list("id", flat=True)[:SEARCH_LIMIT])
        matches = ApplicationModel.objects.filter(applicant_id__in=applicant_ids)
    rows = list(matches.order_by("-created_at")[:SEARCH_LIMIT])
    emails = dict(UserModel.objects.filter(id__in=[row.applicant_id for row in rows]).values_list("id", "email"))
    titles = dict(CompetitionModel.objects.filter(id__in=[row.competition_id for row in rows]).values_list("id", "title"))
    return [
        Target(
            kind="application",
            id=str(row.id),
            label=emails.get(row.applicant_id) or str(row.id),
            hint=f"{titles.get(row.competition_id, '—')} · {row.status}",
        )
        for row in rows
    ]


def _organization_candidates(query: str) -> list[Target]:
    if (identifier := _maybe_uuid(query)) is not None:
        matches = OrganizationModel.objects.filter(id=identifier)
    else:
        matches = OrganizationModel.objects.filter(name__icontains=query) | OrganizationModel.objects.filter(slug__icontains=query)
    return [
        Target(kind="organization", id=str(row.id), label=row.name, hint=f"/{row.slug} · {row.status}")
        for row in matches.order_by("name")[:SEARCH_LIMIT]
    ]


def _account_candidates(query: str) -> list[Target]:
    if (identifier := _maybe_uuid(query)) is not None:
        matches = UserModel.objects.filter(id=identifier)
    else:
        matches = (
            UserModel.objects.filter(email__icontains=query)
            | UserModel.objects.filter(last_name__icontains=query)
            | UserModel.objects.filter(phone__icontains=query)
        )
    return [
        Target(
            kind="account",
            id=str(row.id),
            label=row.email,
            hint=" ".join(part for part in (row.last_name, row.first_name) if part) or "—",
        )
        for row in matches.order_by("email")[:SEARCH_LIMIT]
    ]


def _participant_candidates(query: str) -> list[Target]:
    if (identifier := _maybe_uuid(query)) is not None:
        matches = ParticipantRegistryModel.objects.filter(id=identifier)
    else:
        matches = (
            ParticipantRegistryModel.objects.filter(last_name__icontains=query)
            | ParticipantRegistryModel.objects.filter(first_name__icontains=query)
            | ParticipantRegistryModel.objects.filter(collective_name__icontains=query)
        )
    rows = list(matches.order_by("last_name", "first_name")[:SEARCH_LIMIT])
    emails = dict(UserModel.objects.filter(id__in=[row.owner_id for row in rows]).values_list("id", "email"))
    return [
        Target(
            kind="participant",
            id=str(row.id),
            label=row.collective_name or " ".join(part for part in (row.last_name, row.first_name) if part) or str(row.id),
            hint=f"{emails.get(row.owner_id, '—')} · {row.birth_date:%d.%m.%Y}",
        )
        for row in rows
    ]


def _teacher_candidates(query: str) -> list[Target]:
    if (identifier := _maybe_uuid(query)) is not None:
        matches = TeacherModel.objects.filter(id=identifier)
    else:
        matches = TeacherModel.objects.filter(last_name__icontains=query) | TeacherModel.objects.filter(first_name__icontains=query)
    rows = list(matches.order_by("last_name", "first_name")[:SEARCH_LIMIT])
    emails = dict(UserModel.objects.filter(id__in=[row.owner_id for row in rows]).values_list("id", "email"))
    return [
        Target(
            kind="teacher",
            id=str(row.id),
            label=" ".join(part for part in (row.last_name, row.first_name) if part) or str(row.id),
            hint=f"{emails.get(row.owner_id, '—')} · {row.role}",
        )
        for row in rows
    ]


_SEARCH: dict[str, Callable[[str], list[Target]]] = {
    "festival": _festival_candidates,
    "program": _program_candidates,
    "application": _application_candidates,
    "organization": _organization_candidates,
    "template": _template_candidates,
    "account": _account_candidates,
    "participant": _participant_candidates,
    "teacher": _teacher_candidates,
}


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------


def _ids(queryset: Any) -> list[uuid.UUID]:
    return list(queryset.values_list("id", flat=True))


def _organization_names(organization_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
    return dict(OrganizationModel.objects.filter(id__in=list(organization_ids)).values_list("id", "name"))


def _item_counts(program_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many slots each programme holds — the scale of what a deletion would take."""
    rows = ProgramItemModel.objects.filter(program_id__in=program_ids).values("program_id").annotate(total=Count("id"))
    return {row["program_id"]: row["total"] for row in rows}


def _document_type_label(value: str) -> str:
    """The kind of document a template produces, as the operator reads it."""
    return dict(DocumentTypeChoices.choices).get(value, value)


def _sole_owner_of(user_id: uuid.UUID) -> list[str]:
    """Organizations this account is the last standing OWNER of.

    Not a refusal — an operator erasing an account on request should not be blocked
    by an organization that is being wound down anyway. It is a warning because the
    organization is about to become unmanageable from inside, and the operator is
    the only one who can hand it a new owner.
    """
    active = {"role": StaffRoleChoices.OWNER, "status": MembershipStatusChoices.ACTIVE, "deleted_at__isnull": True}
    organization_ids = list(StaffMembershipModel.objects.filter(user_id=user_id, **active).values_list("organization_id", flat=True))
    alone = [
        organization_id
        for organization_id in organization_ids
        if not StaffMembershipModel.objects.filter(organization_id=organization_id, **active).exclude(user_id=user_id).exists()
    ]
    return [name for _id, name in OrganizationModel.objects.filter(id__in=alone).values_list("id", "name")]


def _as_uuid(value: str) -> uuid.UUID:
    parsed = _maybe_uuid(value)
    if parsed is None:
        raise TargetNotFoundError(f"{value!r} не похоже на идентификатор.")
    return parsed


def _maybe_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError, TypeError):
        return None


def _normalise(value: str) -> str:
    return " ".join((value or "").split()).casefold()
