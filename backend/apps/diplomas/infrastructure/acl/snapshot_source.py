"""``DjangoDiplomaSnapshotSource`` — builds a diploma's frozen snapshot.

Reads the Applications context (the submission) and the Competitions context
(the competition and its taxonomy) by id, plus the participant's organization
from the Participants context — the same cross-context reads the organizer
registry read model performs. Produces resolved *values*; anything absent is
left ``None`` (a diploma never carries a placeholder). ``award.degree`` is always
``None`` here — the jury result is filled in later.
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
from apps.diplomas.application.interfaces import SnapshotBuild
from apps.diplomas.domain.value_objects import (
    AwardSnapshot,
    CompetitionSnapshot,
    DiplomaSnapshot,
    NominationSnapshot,
    OrganizationSnapshot,
    ParticipantSnapshot,
    PerformanceSnapshot,
    TeacherSnapshot,
)
from apps.diplomas.infrastructure.models import TemplateModel
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel

__all__ = ["DjangoDiplomaSnapshotSource"]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _lead_participant(submission: SubmissionModel) -> dict[str, Any]:
    for participant in submission.participants or []:
        if _clean(participant.get("display_name")):
            return participant
    participants = submission.participants or []
    return participants[0] if participants else {}


def _age(participant: dict[str, Any]) -> int | None:
    raw = _clean(participant.get("birth_date"))
    if raw is None:
        return None
    try:
        born = date.fromisoformat(raw)
    except ValueError:
        return None
    today = date.today()
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return years if years >= 0 else None


def _teachers(submission: SubmissionModel) -> tuple[TeacherSnapshot, ...]:
    result: list[TeacherSnapshot] = []
    for teacher in submission.teachers or []:
        name = " ".join(
            part
            for part in (
                _clean(teacher.get("last_name")),
                _clean(teacher.get("first_name")),
                _clean(teacher.get("middle_name")),
            )
            if part
        )
        if name:
            result.append(TeacherSnapshot(name=name, role=_clean(teacher.get("role"))))
    return tuple(result)


def _taxonomy_name(model: Any, row_id: str | None) -> str | None:
    if not row_id:
        return None
    name = model.objects.filter(id=row_id, deleted_at__isnull=True).values_list("name", flat=True).first()
    return _clean(name)


def _organization(participant: dict[str, Any]) -> OrganizationSnapshot:
    registry_id = _clean(participant.get("registry_participant_id"))
    if registry_id is None:
        return OrganizationSnapshot()
    try:
        participant_uuid = uuid.UUID(registry_id)
    except ValueError:
        return OrganizationSnapshot()
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
        return OrganizationSnapshot()
    return OrganizationSnapshot(name=_clean(membership.organization.name))


class DjangoDiplomaSnapshotSource:
    """Concrete ``DiplomaSnapshotSource`` over Django ORM cross-context reads."""

    def template_exists(self, template_id: uuid.UUID) -> bool:
        return TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists()

    def list_submission_ids(
        self, competition_id: uuid.UUID, *, category_id: uuid.UUID | None = None
    ) -> list[uuid.UUID]:
        rows = SubmissionModel.objects.filter(
            competition_id=competition_id, deleted_at__isnull=True
        )
        if category_id is not None:
            # nomination == performance.nomination_id (Applications embeds it as JSON).
            rows = rows.filter(performance__nomination_id=str(category_id))
        return list(rows.order_by("created_at").values_list("id", flat=True))

    def build(self, submission_id: uuid.UUID) -> SnapshotBuild | None:
        submission = SubmissionModel.objects.filter(id=submission_id, deleted_at__isnull=True).first()
        if submission is None:
            return None

        lead = _lead_participant(submission)
        performance = submission.performance or {}
        competition = CompetitionModel.objects.filter(id=submission.competition_id, deleted_at__isnull=True).first()

        nomination = NominationSnapshot(
            title=_taxonomy_name(CategoryModel, _clean(performance.get("nomination_id"))),
            discipline=_taxonomy_name(DisciplineModel, _clean(performance.get("discipline_id"))),
            participant_group=_taxonomy_name(ParticipantGroupModel, _clean(performance.get("participant_group_id"))),
            age_category=_taxonomy_name(AgeCategoryModel, _clean(performance.get("age_category_id"))),
        )

        competition_snapshot = CompetitionSnapshot()
        if competition is not None:
            competition_snapshot = CompetitionSnapshot(
                title=_clean(competition.title),
                date=(competition.competition_start.strftime("%d.%m.%Y") if competition.competition_start is not None else None),
                city=_clean(competition.venue_name) or _clean(competition.venue_address),
            )

        snapshot = DiplomaSnapshot(
            participant=ParticipantSnapshot(
                display_name=_clean(lead.get("display_name")) or "",
                age=_age(lead),
            ),
            teachers=_teachers(submission),
            organization=_organization(lead),
            nomination=nomination,
            performance=PerformanceSnapshot(title=_clean(performance.get("title"))),
            competition=competition_snapshot,
            # The jury result is unknown at creation — filled in later.
            award=AwardSnapshot(degree=None),
        )
        return SnapshotBuild(competition_id=submission.competition_id, snapshot=snapshot)
