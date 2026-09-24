"""``DjangoPerformanceDirectory`` — the acts, as a jury is allowed to see them.

Reads the Applications context (which entries are competing and where they sit in the
taxonomy) and the Programs context (the number each was announced under), and hands back
:class:`DirectoryPerformance` values in this context's language (ARCH-001 §13.3).

**Names are deliberately absent.** ADR-0013 says a jury sees pseudonymized work, and the
organizer confirmed the panel's tablet shows the number and the name of the act and no
participants. That rule is kept *here*, at the boundary, rather than in a serializer:
a projection that never carries a child's name cannot leak one, however the screens
above it are later rewritten.

The studio is the one exception, and it names an institution rather than a person — a
panel is routinely asked which school an act came from, and that question is about the
school.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Final

from apps.applications.domain.value_objects import SubmissionStatus
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipationFormatModel,
)
from apps.judging.application.interfaces import DirectoryPerformance
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel
from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel
from apps.programs.infrastructure.models.program import ProgramItemKindChoices

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoPerformanceDirectory"]

#: The statuses in which an entry is actually competing, and therefore the only ones a
#: jury may be handed. Spelled out again rather than imported from Results: the two
#: contexts must be free to disagree later, and this one decides what reaches a tablet.
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


def _uuid(value: Any) -> uuid.UUID | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        return uuid.UUID(text)
    except (ValueError, TypeError):
        return None


class DjangoPerformanceDirectory:
    """Concrete :class:`~apps.judging.application.interfaces.PerformanceDirectory`."""

    def performances(self, competition_id: uuid.UUID) -> tuple[DirectoryPerformance, ...]:
        """Every competing act of the festival, in running order where there is one.

        Acts with no slot in any programme come last, ordered by genre and title: a
        festival that judges online without ever building a programme is perfectly
        normal, and its panel still needs the list.
        """
        models = list(
            SubmissionModel.objects.filter(
                competition_id=competition_id,
                status__in=COMPETING_SUBMISSION_STATUSES,
                deleted_at__isnull=True,
                performance__isnull=False,
            )
        )
        resolved = self._resolve(models, competition_id=competition_id)
        return tuple(sorted(resolved, key=_running_order_key))

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, DirectoryPerformance]:
        """Resolve the acts a set of marks point at.

        Not filtered by status: a card written for an entry that was withdrawn afterwards
        still has to render on the organizer's tally, because that is exactly the line
        somebody will ask about.
        """
        if not submission_ids:
            return {}
        models = list(
            SubmissionModel.objects.filter(
                id__in=list(submission_ids),
                deleted_at__isnull=True,
                performance__isnull=False,
            )
        )
        competition_id = models[0].competition_id if models else None
        return {item.submission_id: item for item in self._resolve(models, competition_id=competition_id)}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(self, models: list[SubmissionModel], *, competition_id: uuid.UUID | None) -> list[DirectoryPerformance]:
        if not models:
            return []
        taxonomy = self._taxonomy(models)
        numbers = self._numbers(competition_id) if competition_id is not None else {}
        organizations = self._organizations(models)
        performances: list[DirectoryPerformance] = []
        for model in models:
            performance = model.performance or {}
            category_id = _uuid(performance.get("nomination_id"))
            if category_id is None:
                # An entry with no genre cannot be judged: there is no criteria sheet to
                # give a judge and no protocol for the result to land in.
                continue
            discipline_id = _uuid(performance.get("discipline_id"))
            age_category_id = _uuid(performance.get("age_category_id"))
            format_id = _uuid(performance.get("participation_format_id"))
            performances.append(
                DirectoryPerformance(
                    submission_id=model.id,
                    title=_clean(performance.get("title")) or "Без названия",
                    category_id=category_id,
                    discipline_id=discipline_id,
                    age_category_id=age_category_id,
                    participation_format_id=format_id,
                    number=numbers.get(model.id, 0),
                    category_name=taxonomy["category"].get(str(category_id)),
                    discipline_name=taxonomy["discipline"].get(str(discipline_id)) if discipline_id else None,
                    age_category_name=taxonomy["age_category"].get(str(age_category_id)) if age_category_id else None,
                    participation_format_name=taxonomy["format"].get(str(format_id)) if format_id else None,
                    organization=organizations.get(str(model.id)),
                )
            )
        return performances

    @staticmethod
    def _numbers(competition_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """Submission id → the number it was announced under, across every programme.

        The first occurrence wins when an act somehow sits in two programmes: that is the
        number participants were told, and the one the hall's board should read.
        """
        program_ids = list(
            ProgramModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True)
        )
        if not program_ids:
            return {}
        rows = (
            ProgramItemModel.objects.filter(
                program_id__in=program_ids,
                kind=ProgramItemKindChoices.PERFORMANCE,
                submission_id__isnull=False,
                deleted_at__isnull=True,
            )
            .order_by("program__created_at", "position")
            .values_list("submission_id", "number", "position")
        )
        numbers: dict[uuid.UUID, int] = {}
        for submission_id, number, position in rows:
            if submission_id is None or submission_id in numbers:
                continue
            numbers[submission_id] = int(number) or int(position)
        return numbers

    @staticmethod
    def _taxonomy(models: list[SubmissionModel]) -> dict[str, dict[str, str]]:
        """One id→name map per taxonomy axis, built from one query each."""
        wanted: dict[str, set[str]] = {"category": set(), "discipline": set(), "age_category": set(), "format": set()}
        for model in models:
            performance = model.performance or {}
            for axis, key in (
                ("category", "nomination_id"),
                ("discipline", "discipline_id"),
                ("age_category", "age_category_id"),
                ("format", "participation_format_id"),
            ):
                value = _clean(performance.get(key))
                if value:
                    wanted[axis].add(value)

        def names(model: Any, ids: set[str]) -> dict[str, str]:
            if not ids:
                return {}
            rows = model.objects.filter(id__in=list(ids), deleted_at__isnull=True).values_list("id", "name")
            return {str(row_id): str(name) for row_id, name in rows}

        return {
            "category": names(CategoryModel, wanted["category"]),
            "discipline": names(DisciplineModel, wanted["discipline"]),
            "age_category": names(AgeCategoryModel, wanted["age_category"]),
            "format": names(ParticipationFormatModel, wanted["format"]),
        }

    @staticmethod
    def _organizations(models: list[SubmissionModel]) -> dict[str, str]:
        """Submission id → the lead participant's primary educational organization."""
        registry_by_submission: dict[str, str] = {}
        for model in models:
            for entry in model.participants or []:
                registry_id = _clean(entry.get("registry_participant_id"))
                if registry_id:
                    registry_by_submission[str(model.id)] = registry_id
                    break
        if not registry_by_submission:
            return {}
        memberships = (
            ParticipantOrganizationMembershipModel.objects.filter(
                participant_id__in=list(set(registry_by_submission.values())),
                deleted_at__isnull=True,
            )
            .select_related("organization")
            .order_by("-is_primary")
        )
        by_participant: dict[str, str] = {}
        for membership in memberships:
            by_participant.setdefault(str(membership.participant_id), str(membership.organization.name))
        return {
            submission_id: by_participant[registry_id]
            for submission_id, registry_id in registry_by_submission.items()
            if registry_id in by_participant
        }


def _running_order_key(item: DirectoryPerformance) -> tuple[int, int, str, str]:
    """Numbered acts first in programme order, then the rest by genre and title."""
    return (0, item.number, "", "") if item.number else (1, 0, (item.category_name or "").lower(), item.title.lower())
