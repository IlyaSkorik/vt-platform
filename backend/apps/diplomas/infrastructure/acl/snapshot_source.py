"""``DjangoDiplomaSnapshotSource`` — builds a diploma's frozen snapshot.

Reads the Applications context (the submission) and the Competitions context
(the competition and its taxonomy) by id, plus the participant's organization
from the Participants context — the same cross-context reads the organizer
registry read model performs. Produces resolved *values*; anything absent is
left ``None`` (a diploma never carries a placeholder). ``award.degree`` is always
``None`` here — the jury result is filled in later.

Also owns the answer to *which* of a competition's submissions a document is due
for: see :data:`COMPETING_SUBMISSION_STATUSES`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, Final

from apps.applications.domain.value_objects import SubmissionStatus
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

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoDiplomaSnapshotSource"]

#: The statuses in which an entry is actually taking part in the competition, and
#: therefore the only ones a document is issued for.
#:
#: Applications' lifecycle is linear and, past ``ACCEPTED``, irreversible: an entry
#: cannot be cancelled from there on and its content is frozen (see
#: ``_LEGAL_TRANSITIONS`` in :mod:`apps.applications.domain.entities`). ``ACCEPTED``
#: onward is exactly "committed to the running order", which is what a diploma or a
#: thank-you letter attests.
#:
#: Everything earlier is a decision not yet made — under review, returned for
#: correction, approved but unpaid — and ``CANCELLED`` is a decision made the other
#: way. Printing for those would put a name on a diploma for a performance that may
#: never happen, and the diploma register is immutable once written.
COMPETING_SUBMISSION_STATUSES: Final[tuple[str, ...]] = (
    SubmissionStatus.ACCEPTED.value,
    SubmissionStatus.SCHEDULED.value,
    SubmissionStatus.COMPLETED.value,
)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _lead_participant(submission: SubmissionModel) -> dict[str, Any]:
    # `participants` is a JSON column — see the identical narrowing in the preview
    # builder; the rows are untyped until checked.
    participants = [row for row in submission.participants or [] if isinstance(row, dict)]
    for participant in participants:
        if _clean(participant.get("display_name")):
            return participant
    return participants[0] if participants else {}


def _performers(submission: SubmissionModel) -> str:
    """Every participant the entry named, in the order the applicant added them.

    An entry may carry more than one participant row — a duet is two of them — and a
    diploma is issued once, for the entry, so the sheet has to name all of them. The
    single-valued fields beside the name (age, organization, a collective's roster) still
    come from the lead row: they belong to one person and cannot be joined.
    """
    rows = [row for row in submission.participants or [] if isinstance(row, dict)]
    return ", ".join(name for row in rows if (name := _clean(row.get("display_name"))))


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


def _members(participant: dict[str, Any]) -> tuple[str, ...]:
    """The people named inside a collective, as the applicant typed them.

    The Applications context already normalized this list (trimmed, blank-free,
    de-duplicated) when the applicant saved it; re-cleaning here is the same defence
    every other read in this module applies to a JSON column, not a second rule.

    Read from the **lead** participant only, like every other field of the snapshot: an
    individual diploma names its member *and* the collective they performed in, and the
    collective it names is the lead one. Taking rosters from a second participant row
    would print those people under the wrong ensemble's name.
    """
    raw = participant.get("members")
    if not isinstance(raw, list):
        return ()
    names: list[str] = []
    for row in raw:
        name = _clean(row)
        if name is not None:
            names.append(name)
    return tuple(names)


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


def _competition_year(competition: CompetitionModel | None) -> int | None:
    """The year the competition is *held* — the year printed in diploma numbers.

    The competition's own start date first; the ``season`` label (e.g. "2026") as
    a fallback for a competition whose dates are not set yet. Never the system
    year: a 2026 competition keeps 2026 in its numbers however late it prints.
    """
    if competition is None:
        return None
    if competition.competition_start is not None:
        return competition.competition_start.year
    season = _clean(competition.season)
    if season is not None and season.isdigit() and len(season) == 4:
        return int(season)
    return None


def _organization(participant: dict[str, Any]) -> OrganizationSnapshot:
    """The institution this diploma prints for the lead performer.

    An organizer who corrected the institution on the entry corrected it *for the
    paperwork*, which is what this is — so that answer wins outright and no registry
    lookup happens. Absent (every entry nobody corrected, including all of them from
    before the field existed), the applicant's Participant Registry answers as before.
    """
    pinned = _clean(participant.get("organization_name"))
    if pinned is not None:
        return OrganizationSnapshot(name=pinned)
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
        self,
        competition_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        discipline_id: uuid.UUID | None = None,
        exclude_discipline_ids: Sequence[uuid.UUID] = (),
    ) -> list[uuid.UUID]:
        """The entries a document is due for, narrowed to a genre/nomination if asked.

        Only entries actually in the competition — see
        :data:`COMPETING_SUBMISSION_STATUSES`. A cancelled or still-under-review
        entry is not skipped later in the pipeline; it never enters it.
        """
        rows = SubmissionModel.objects.filter(
            competition_id=competition_id,
            deleted_at__isnull=True,
            status__in=COMPETING_SUBMISSION_STATUSES,
        )
        if category_id is not None:
            # genre == performance.nomination_id (Applications embeds it as JSON).
            rows = rows.filter(performance__nomination_id=str(category_id))
        ordered = rows.order_by("created_at")
        if discipline_id is None and not exclude_discipline_ids:
            return list(ordered.values_list("id", flat=True))

        # Narrowing by nomination is done here rather than in SQL, because the
        # exclusion cannot be: `performance` is a JSON column, and excluding on a
        # key an entry does not carry evaluates to NULL — which drops every entry
        # that names no nomination along with the ones that were meant to go. Those
        # entries are exactly the ones the genre's default template is for, so the
        # bug would silently leave most of a festival unprinted.
        wanted = str(discipline_id) if discipline_id is not None else None
        excluded = {str(item) for item in exclude_discipline_ids}
        selected: list[uuid.UUID] = []
        for row in ordered.values("id", "performance"):
            entry_discipline = str((row["performance"] or {}).get("discipline_id") or "")
            if wanted is not None:
                if entry_discipline == wanted:
                    selected.append(row["id"])
            elif entry_discipline not in excluded:
                selected.append(row["id"])
        return selected

    def discipline_ids(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID | None]:
        """The nomination each of these entries performs in, by submission id."""
        if not submission_ids:
            return {}
        found: dict[uuid.UUID, uuid.UUID | None] = {}
        for row in SubmissionModel.objects.filter(id__in=list(submission_ids), deleted_at__isnull=True).values("id", "performance"):
            raw = _clean((row["performance"] or {}).get("discipline_id"))
            try:
                found[row["id"]] = uuid.UUID(raw) if raw else None
            except ValueError:
                # A stored id that is not a UUID reads as "no nomination": the entry
                # then prints on its genre's template, which is what it did before
                # nominations could carry one of their own.
                found[row["id"]] = None
        return found

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
                display_name=_performers(submission),
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
        return SnapshotBuild(
            competition_id=submission.competition_id,
            snapshot=snapshot,
            competition_year=_competition_year(competition),
            members=_members(lead),
        )
