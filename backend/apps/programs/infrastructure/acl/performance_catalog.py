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
from apps.identity.infrastructure.models.user import UserModel
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel
from apps.programs.application.interfaces import CatalogPerformance
from apps.teachers.infrastructure.models import TeacherModel

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


def _headcount(entries: list[dict[str, Any]] | None) -> int:
    """How many people this entry puts on stage.

    The sum of each performer row's ``member_count``: a solo row is one person, and a
    collective row carries the headcount the applicant typed on the form. Falls back to
    one per row for entries filled in before the field existed, which is the honest
    reading - a row that never stated a number is one performer.
    """
    total = 0
    for entry in entries or []:
        try:
            count = int((entry or {}).get("member_count") or 1)
        except (TypeError, ValueError):
            count = 1
        total += max(1, count)
    return total


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
        age_orders = self._age_orders(models)
        organizations = self._organizations(models)
        contacts = self._contacts(models)
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
                    age_order=age_orders.get(_clean(performance.get("age_category_id")) or ""),
                    participant_group=taxonomy["participant_group"].get(_clean(performance.get("participant_group_id")) or ""),
                    participation_format=taxonomy["format"].get(_clean(performance.get("participation_format_id")) or ""),
                    participants=participants,
                    participant_count=_headcount(model.participants),
                    teachers=teachers,
                    contacts=contacts.get(str(model.id), ()),
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
    def _age_orders(models: list[SubmissionModel]) -> dict[str, int]:
        """Age-band id → its rank among the bands this batch uses, youngest first.

        A rank rather than the raw ``sort_order``, because that column defaults to 0 for
        every band a competition never bothered to order by hand - at which point the
        ages themselves are the only honest ordering left. Ranking is what lets a
        generated programme put "7-9 лет" before "10-12 лет" instead of sorting the
        names as text.
        """
        wanted = {value for value in (_clean((model.performance or {}).get("age_category_id")) for model in models) if value}
        if not wanted:
            return {}
        rows = AgeCategoryModel.objects.filter(id__in=list(wanted), deleted_at__isnull=True).values_list("id", "sort_order", "min_age", "max_age")
        ranked = sorted(rows, key=lambda row: (int(row[1]), int(row[2]), int(row[3])))
        return {str(row[0]): rank for rank, row in enumerate(ranked)}

    @staticmethod
    def _contacts(models: list[SubmissionModel]) -> dict[str, tuple[str, ...]]:
        """Submission id → the phones to ring about this act, in the order to try them.

        The teachers first: they are the people standing in the wings, and the entry
        carries only their names and a reference into the cabinet's directory - the phone
        itself lives there. The applicant's own number is the fallback for an act with no
        teacher, or whose teachers were typed in by hand and so have nowhere to ring.

        A fallback rather than an addition: a programme cell is read at a glance on the
        day, and "позвонить педагогу, а если его нет - тому, кто подал заявку" is one
        decision, not two numbers for the organizer to choose between mid-performance.

        Two queries for the whole batch, however many rows it holds.
        """
        directory_ids: set[str] = set()
        teachers_by_submission: dict[str, list[str]] = {}
        for model in models:
            ids = [value for entry in model.teachers or [] if (value := _clean((entry or {}).get("directory_teacher_id")))]
            teachers_by_submission[str(model.id)] = ids
            directory_ids.update(ids)
        teacher_phones: dict[str, str] = {}
        if directory_ids:
            teacher_rows = TeacherModel.objects.filter(id__in=list(directory_ids), deleted_at__isnull=True).values_list("id", "phone")
            teacher_phones = {str(teacher_id): cleaned for teacher_id, phone in teacher_rows if (cleaned := _clean(phone))}
        applicant_phones: dict[str, str] = {}
        wanted_applicants = {str(model.applicant_id) for model in models}
        if wanted_applicants:
            user_rows = UserModel.objects.filter(id__in=list(wanted_applicants), deleted_at__isnull=True).values_list("id", "phone")
            applicant_phones = {str(user_id): cleaned for user_id, phone in user_rows if (cleaned := _clean(phone))}
        contacts: dict[str, tuple[str, ...]] = {}
        for model in models:
            submission_id = str(model.id)
            # De-duplicated with a dict rather than a set: two teachers sharing a number
            # is one number, and the order they were named in is the order to try them.
            found = dict.fromkeys(
                phone for teacher_id in teachers_by_submission[submission_id] if (phone := teacher_phones.get(teacher_id)) is not None
            )
            if not found:
                fallback = applicant_phones.get(str(model.applicant_id))
                if fallback is not None:
                    found = {fallback: None}
            if found:
                contacts[submission_id] = tuple(found)
        return contacts

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
