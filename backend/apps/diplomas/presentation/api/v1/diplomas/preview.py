"""Diploma preview data — the BindingResolver.

Given an application (a submission), resolve the values that fill a template's
data-bound fields, keyed by binding (e.g. ``participant.display_name``). Reads the
Applications and Competitions contexts by id (cross-context reads, exactly as the
organizer registry read model does); the diplomas context owns none of these rows.

Bindings are dotted business keys, never storage columns. The catalogue
(:data:`BINDINGS`) is the single seam a new field extends: add a key here, teach
:func:`resolve_preview_bindings` how to produce its value, and the editor needs no
change. Every catalogue key is always present in the resolved map — a value that
cannot be produced (no source row, empty field, or a source not wired yet such as
awards) resolves to :data:`MISSING` (an empty string, so the field renders nothing),
never raising.

`participant.display_name` is the performer's single display name — the
individual's full name for a solo entry or the ensemble's name for a collective
— exactly the unified field the editor binds to.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
)
from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel

__all__ = [
    "BINDINGS",
    "MEMBER_FULL_NAME",
    "MISSING",
    "PARTICIPANT_DISPLAY_NAME",
    "list_preview_applications",
    "resolve_preview_bindings",
]

# --- Binding catalogue (business keys) --------------------------------------

PARTICIPANT_DISPLAY_NAME = "participant.display_name"
PARTICIPANT_AGE = "participant.age"
MEMBER_FULL_NAME = "member.full_name"
TEACHER_DISPLAY_NAME = "teacher.display_name"
ORGANIZATION_NAME = "organization.name"
NOMINATION_TITLE = "nomination.title"
NOMINATION_DISCIPLINE = "nomination.discipline"
NOMINATION_PARTICIPANT_GROUP = "nomination.participant_group"
NOMINATION_AGE_CATEGORY = "nomination.age_category"
PERFORMANCE_TITLE = "performance.title"
COMPETITION_TITLE = "competition.title"
COMPETITION_DATE = "competition.date"
COMPETITION_CITY = "competition.city"
AWARD_DEGREE = "award.degree"
DIPLOMA_NUMBER = "diploma.number"
DIPLOMA_ISSUE_DATE = "diploma.issue_date"

#: Every binding the editor may place. Mirrors the frontend Binding Catalog.
BINDINGS: tuple[str, ...] = (
    PARTICIPANT_DISPLAY_NAME,
    PARTICIPANT_AGE,
    MEMBER_FULL_NAME,
    TEACHER_DISPLAY_NAME,
    ORGANIZATION_NAME,
    NOMINATION_TITLE,
    NOMINATION_DISCIPLINE,
    NOMINATION_PARTICIPANT_GROUP,
    NOMINATION_AGE_CATEGORY,
    PERFORMANCE_TITLE,
    COMPETITION_TITLE,
    COMPETITION_DATE,
    COMPETITION_CITY,
    AWARD_DEGREE,
    DIPLOMA_NUMBER,
    DIPLOMA_ISSUE_DATE,
)

#: Value for any binding that cannot be produced: an empty string, so an unfilled
#: field renders as nothing rather than a placeholder dash. The UI never crashes on
#: a gap; a resolver never raises. Matches the frontend ``MISSING_VALUE``.
MISSING = ""


# --- Small pure helpers -----------------------------------------------------


def _clean(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lead_participant(submission: SubmissionModel) -> dict[str, Any]:
    """The first participant carrying a display name (the one a diploma names)."""
    # `participants` is a JSON column, so its rows arrive untyped; narrowing here stops
    # that Any escaping into the caller as a "dict" it never verified.
    participants = [row for row in submission.participants or [] if isinstance(row, dict)]
    for participant in participants:
        if _clean(participant.get("display_name")):
            return participant
    return participants[0] if participants else {}


def _performer_name(submission: SubmissionModel) -> str:
    return _clean(_lead_participant(submission).get("display_name"))


def _age_of(participant: dict[str, Any]) -> str:
    """Whole years at today's date (birthday-aware), or ``MISSING`` if unknown."""
    raw = _clean(participant.get("birth_date"))
    if not raw:
        return MISSING
    try:
        born = date.fromisoformat(raw)
    except ValueError:
        return MISSING
    today = date.today()
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return str(years) if years >= 0 else MISSING


def _first_member(participant: dict[str, Any]) -> str:
    """The first named member of a collective, or ``MISSING`` if nobody is named."""
    raw = participant.get("members")
    if not isinstance(raw, list):
        return MISSING
    for row in raw:
        name = _clean(row)
        if name:
            return name
    return MISSING


def _person_full_name(entry: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            _clean(entry.get("last_name")),
            _clean(entry.get("first_name")),
            _clean(entry.get("middle_name")),
        )
        if part
    )


def _teacher_roster(submission: SubmissionModel, *, roles: bool = True) -> str:
    """The submission's teachers as ``role: name1, name2`` — one role per line.

    Teachers sharing a role are joined on one line (``Педагог: ФИО1, ФИО2``);
    distinct roles each get their own line, in first-appearance order. A teacher
    with no name is skipped; a teacher with no role shows just the name.

    Without ``roles`` (a thank-you letter) the names alone, comma-separated —
    matching what the renderer prints for that kind, so the editor's preview does
    not promise a format the PDF will not use.
    """
    if not roles:
        names = [name for teacher in submission.teachers or [] if (name := _person_full_name(teacher))]
        return ", ".join(names) or MISSING

    order: list[str] = []
    names_by_role: dict[str, list[str]] = {}
    for teacher in submission.teachers or []:
        name = _person_full_name(teacher)
        if not name:
            continue
        role = _clean(teacher.get("role"))
        if role not in names_by_role:
            names_by_role[role] = []
            order.append(role)
        names_by_role[role].append(name)
    if not order:
        return MISSING
    lines = [f"{role}: {', '.join(names_by_role[role])}" if role else ", ".join(names_by_role[role]) for role in order]
    return "\n".join(lines)


def _taxonomy_name(model: Any, row_id: str) -> str:
    """The ``name`` of one taxonomy row by id, or ``MISSING``."""
    if not row_id:
        return MISSING
    name = model.objects.filter(id=row_id, deleted_at__isnull=True).values_list("name", flat=True).first()
    return _clean(name) or MISSING


def _organization_name(participant: dict[str, Any]) -> str:
    """The participant's primary educational organization (via the registry link).

    Mirrors the organizer registry read model: a participant's organization is not
    on the submission but in the Participants context, keyed by the
    ``registry_participant_id`` the submission denormalizes.
    """
    registry_id = _clean(participant.get("registry_participant_id"))
    if not registry_id:
        return MISSING
    try:
        participant_uuid = uuid.UUID(registry_id)
    except ValueError:
        return MISSING
    membership = (
        ParticipantOrganizationMembershipModel.objects.filter(
            participant_id=participant_uuid,
            deleted_at__isnull=True,
            organization__deleted_at__isnull=True,
        )
        .select_related("organization")
        .order_by("-is_primary", "organization__name")
        .first()
    )
    if membership is None:
        return MISSING
    return _clean(membership.organization.name) or MISSING


# --- Public API -------------------------------------------------------------


def list_preview_applications(competition_id: str) -> list[dict[str, Any]]:
    """Applications (submissions) of a competition, labelled by performer name."""
    rows = SubmissionModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("-created_at")
    applications: list[dict[str, Any]] = []
    for row in rows:
        performance = row.performance or {}
        label = _performer_name(row) or _clean(performance.get("title"))
        applications.append({"id": str(row.id), "label": label or str(row.id)[:8].upper()})
    return applications


def resolve_preview_bindings(application_id: str, *, document_type: str = "DIPLOMA") -> dict[str, str] | None:
    """The binding→value map for one application, or None if it does not exist.

    Every key in :data:`BINDINGS` is present; unresolved values are :data:`MISSING`.

    ``document_type`` selects the kind's formatting rules — currently whether the
    teacher roster carries roles — so the editor previews what will actually print.
    """
    submission = SubmissionModel.objects.filter(id=application_id, deleted_at__isnull=True).first()
    if submission is None:
        return None
    policy = policy_for(DocumentType(document_type))

    lead = _lead_participant(submission)
    performance = submission.performance or {}
    competition = CompetitionModel.objects.filter(id=submission.competition_id, deleted_at__isnull=True).first()

    values: dict[str, str] = dict.fromkeys(BINDINGS, MISSING)

    values[PARTICIPANT_DISPLAY_NAME] = _clean(lead.get("display_name")) or MISSING
    values[PARTICIPANT_AGE] = _age_of(lead)
    # The first person the applicant named in this collective — the editor is showing
    # what one member's sheet will say, and every other one differs only here.
    values[MEMBER_FULL_NAME] = _first_member(lead)
    values[TEACHER_DISPLAY_NAME] = _teacher_roster(submission, roles=policy.teacher_roles)
    values[ORGANIZATION_NAME] = _organization_name(lead)

    values[NOMINATION_TITLE] = _taxonomy_name(CategoryModel, _clean(performance.get("nomination_id")))
    values[NOMINATION_DISCIPLINE] = _taxonomy_name(DisciplineModel, _clean(performance.get("discipline_id")))
    values[NOMINATION_PARTICIPANT_GROUP] = _taxonomy_name(ParticipantGroupModel, _clean(performance.get("participant_group_id")))
    values[NOMINATION_AGE_CATEGORY] = _taxonomy_name(AgeCategoryModel, _clean(performance.get("age_category_id")))

    values[PERFORMANCE_TITLE] = _clean(performance.get("title")) or MISSING

    if competition is not None:
        values[COMPETITION_TITLE] = _clean(competition.title) or MISSING
        values[COMPETITION_DATE] = competition.competition_start.strftime("%d.%m.%Y") if competition.competition_start is not None else MISSING
        values[COMPETITION_CITY] = _clean(competition.venue_name) or _clean(competition.venue_address) or MISSING

    # award.* and diploma.* have no source wired yet — they stay MISSING.
    return values
