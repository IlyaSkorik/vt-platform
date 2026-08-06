"""``DjangoPerformanceCatalog`` - the Programs context's window onto other contexts.

Reads the Applications context (submissions and their embedded performance) and the
Competitions context (the competition and its taxonomy), and hands back
:class:`CatalogPerformance` values in *this* context's language. Everything outward
of this module - the aggregate, the use cases, the API - is written as if the acts
simply arrived as flat data (ARCH-001 §13.3, Anti-Corruption Layer).

Which acts a program may contain is a decision this module owns: only entries that
are actually taking part. An entry still under review, awaiting payment or cancelled
has no place in a running order, because the running order is what the day is run
from. That is the same rule the Diplomas context applies when deciding whom a diploma
is due for, and it is deliberately spelled out again rather than imported: the two
contexts must be free to disagree later.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Final

from apps.applications.domain.value_objects import SubmissionStatus
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel
from apps.programs.application.interfaces import CatalogPerformance

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoPerformanceCatalog"]

#: The statuses in which an entry is committed to taking part, and therefore the only
#: ones that may occupy a slot in a running order.
#: The attachment kind a backing track is stored under in the Applications context.
_MUSIC: Final = "MUSIC"
#: What the media archive collects: one block on the entry form, so one archive here.
_MEDIA: Final = frozenset({"VIDEO", "IMAGE"})

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


def _person(entry: dict[str, Any]) -> str | None:
    display = _clean(entry.get("display_name"))
    if display:
        return display
    parts = [_clean(entry.get("last_name")), _clean(entry.get("first_name"))]
    joined = " ".join(part for part in parts if part)
    return joined or None


def _teacher(entry: dict[str, Any]) -> str | None:
    parts = [_clean(entry.get("last_name")), _clean(entry.get("first_name")), _clean(entry.get("middle_name"))]
    joined = " ".join(part for part in parts if part)
    return joined or None


class DjangoPerformanceCatalog:
    """Concrete :class:`~apps.programs.application.interfaces.PerformanceCatalog`."""

    def competing_performances(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID | None = None,
    ) -> tuple[CatalogPerformance, ...]:
        """The acts a program of this scope may contain, in a stable order.

        Ordered by nomination, then discipline, then act title, so "все выступления"
        arrives in the shape an organizer expects to start rearranging from rather
        than in insertion order.
        """
        rows = SubmissionModel.objects.filter(
            competition_id=competition_id,
            status__in=COMPETING_SUBMISSION_STATUSES,
            deleted_at__isnull=True,
            performance__isnull=False,
        )
        if nomination_id is not None:
            rows = rows.filter(performance__nomination_id=str(nomination_id))
        models = list(rows)
        resolved = self._resolve(models)
        return tuple(sorted(resolved, key=lambda p: ((p.nomination or "").lower(), (p.discipline or "").lower(), p.title.lower())))

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        """Resolve the acts a program's existing slots point at."""
        if not submission_ids:
            return {}
        models = list(
            SubmissionModel.objects.filter(
                id__in=list(submission_ids),
                deleted_at__isnull=True,
                performance__isnull=False,
            )
        )
        return {performance.submission_id: performance for performance in self._resolve(models)}

    def music_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        """The backing tracks each act uploaded, read straight off the submission rows."""
        return self._references_of_kinds(submission_ids, kinds=frozenset({_MUSIC}))

    def media_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        """The video and photographs each act uploaded, in upload order."""
        return self._references_of_kinds(submission_ids, kinds=_MEDIA)

    @staticmethod
    def _references_of_kinds(submission_ids: Sequence[uuid.UUID], *, kinds: frozenset[str]) -> dict[uuid.UUID, tuple[str, ...]]:
        """File references of the given attachment kinds, keyed by submission.

        One query for the whole set, and acts with nothing of that kind are simply absent
        from the result — the caller distinguishes "brought none" from "not asked about"
        by which ids it passed in.
        """
        if not submission_ids:
            return {}
        rows = SubmissionModel.objects.filter(id__in=list(submission_ids), deleted_at__isnull=True).values_list("id", "attachments")
        references: dict[uuid.UUID, tuple[str, ...]] = {}
        for submission_id, attachments in rows:
            files = tuple(
                reference
                for reference in (_clean((entry or {}).get("file")) for entry in attachments or [] if (entry or {}).get("type") in kinds)
                if reference
            )
            if files:
                references[submission_id] = files
        return references

    def competition_title(self, competition_id: uuid.UUID) -> str | None:
        title = CompetitionModel.objects.filter(id=competition_id, deleted_at__isnull=True).values_list("title", flat=True).first()
        return _clean(title)

    def nomination_title(self, nomination_id: uuid.UUID) -> str | None:
        name = CategoryModel.objects.filter(id=nomination_id, deleted_at__isnull=True).values_list("name", flat=True).first()
        return _clean(name)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(self, models: list[SubmissionModel]) -> list[CatalogPerformance]:
        """Turn submission rows into flat catalog values, batching every lookup."""
        if not models:
            return []
        taxonomy = self._taxonomy(models)
        organizations = self._organizations(models)
        performances: list[CatalogPerformance] = []
        for model in models:
            performance = model.performance or {}
            try:
                duration_seconds = int(performance.get("duration_seconds") or 0)
            except (TypeError, ValueError):
                duration_seconds = 0
            if duration_seconds <= 0:
                # A slot must have a length; an act with none cannot be scheduled and
                # is therefore not offered as a candidate.
                continue
            participants = tuple(name for name in (_person(entry) for entry in model.participants or []) if name)
            teachers = tuple(name for name in (_teacher(entry) for entry in model.teachers or []) if name)
            nomination_id = _clean(performance.get("nomination_id"))
            performances.append(
                CatalogPerformance(
                    submission_id=model.id,
                    title=_clean(performance.get("title")) or "Без названия",
                    duration_seconds=duration_seconds,
                    nomination_id=uuid.UUID(nomination_id) if nomination_id else None,
                    nomination=taxonomy["nomination"].get(nomination_id or ""),
                    discipline=taxonomy["discipline"].get(_clean(performance.get("discipline_id")) or ""),
                    age_category=taxonomy["age_category"].get(_clean(performance.get("age_category_id")) or ""),
                    participant_group=taxonomy["participant_group"].get(_clean(performance.get("participant_group_id")) or ""),
                    participation_format=taxonomy["format"].get(_clean(performance.get("participation_format_id")) or ""),
                    participants=participants,
                    teachers=teachers,
                    organization=organizations.get(str(model.id)),
                    comment=_clean(performance.get("comment")),
                    status=model.status,
                )
            )
        return performances

    @staticmethod
    def _taxonomy(models: list[SubmissionModel]) -> dict[str, dict[str, str]]:
        """One id→name map per taxonomy axis, built from two queries."""
        wanted: dict[str, set[str]] = {
            "nomination": set(),
            "discipline": set(),
            "age_category": set(),
            "participant_group": set(),
            "format": set(),
        }
        for model in models:
            performance = model.performance or {}
            for axis, key in (
                ("nomination", "nomination_id"),
                ("discipline", "discipline_id"),
                ("age_category", "age_category_id"),
                ("participant_group", "participant_group_id"),
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
            "nomination": names(CategoryModel, wanted["nomination"]),
            "discipline": names(DisciplineModel, wanted["discipline"]),
            "age_category": names(AgeCategoryModel, wanted["age_category"]),
            "participant_group": names(ParticipantGroupModel, wanted["participant_group"]),
            "format": names(ParticipationFormatModel, wanted["format"]),
        }

    @staticmethod
    def _organizations(models: list[SubmissionModel]) -> dict[str, str]:
        """Submission id → the lead participant's primary educational organization.

        The link is the ``registry_participant_id`` a submission denormalizes, resolved
        through the Participants context in a single query for the whole batch.
        """
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
