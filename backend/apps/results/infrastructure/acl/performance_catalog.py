"""``DjangoPerformanceCatalog`` - the Results context's window onto other contexts.

Reads the Applications context (submissions and their embedded performance), the
Competitions context (the competition and its taxonomy), the Participants context (the
performer's school) and the Identity context (the account a results letter is addressed
to), and hands back :class:`CatalogPerformance` values in *this* context's language.
Everything outward of this module - the aggregate, the use cases, the API - is written as
if the acts simply arrived as flat data (ARCH-001 §13.3, Anti-Corruption Layer).

Which acts may appear in a protocol is a decision this module owns: only entries that
actually took part. An entry still under review, awaiting payment or cancelled has no
result, because it did not perform. That is the same rule the Programs context applies to
a running order and the Diplomas context applies to whom a diploma is due, and it is
deliberately spelled out again here rather than imported: the three contexts must be free
to disagree later, and a protocol is the one of them that becomes a public claim about
what happened.
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
from apps.identity.infrastructure.models import UserModel
from apps.participants.infrastructure.models import ParticipantOrganizationMembershipModel
from apps.results.application.interfaces import CatalogPerformance

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoPerformanceCatalog"]

#: The statuses in which an entry took part, and therefore the only ones a protocol may
#: record a result for.
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
    """Concrete :class:`~apps.results.application.interfaces.PerformanceCatalog`."""

    def competing_performances(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
    ) -> tuple[CatalogPerformance, ...]:
        """The acts of one nomination that took part, in a stable order.

        Ordered by discipline then act title, which is the order an organizer expects to
        start from when there was no programme to seed from.
        """
        rows = SubmissionModel.objects.filter(
            competition_id=competition_id,
            status__in=COMPETING_SUBMISSION_STATUSES,
            deleted_at__isnull=True,
            performance__isnull=False,
            performance__nomination_id=str(nomination_id),
        )
        resolved = self._resolve(list(rows))
        return tuple(sorted(resolved, key=lambda p: ((p.discipline or "").lower(), p.title.lower())))

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        """Resolve the acts a protocol's existing rows point at.

        Deliberately **not** filtered by status: a row must keep rendering its act's name
        even if the entry was later cancelled, because the protocol records what happened
        and an organizer needs to see which line the problem is on. Only an entry deleted
        outright drops out, and the row then renders as "Выступление удалено".
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
        return {performance.submission_id: performance for performance in self._resolve(models)}

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
        applicants = self._applicants(models)
        performances: list[CatalogPerformance] = []
        for model in models:
            performance = model.performance or {}
            nomination_id = _clean(performance.get("nomination_id"))
            applicant = applicants.get(str(model.applicant_id), {})
            performances.append(
                CatalogPerformance(
                    submission_id=model.id,
                    title=_clean(performance.get("title")) or "Без названия",
                    applicant_id=model.applicant_id,
                    applicant_email=applicant.get("email"),
                    applicant_name=applicant.get("name"),
                    nomination_id=uuid.UUID(nomination_id) if nomination_id else None,
                    nomination=taxonomy["nomination"].get(nomination_id or ""),
                    discipline=taxonomy["discipline"].get(_clean(performance.get("discipline_id")) or ""),
                    age_category=taxonomy["age_category"].get(_clean(performance.get("age_category_id")) or ""),
                    participant_group=taxonomy["participant_group"].get(_clean(performance.get("participant_group_id")) or ""),
                    participation_format=taxonomy["format"].get(_clean(performance.get("participation_format_id")) or ""),
                    participants=tuple(name for name in (_person(entry) for entry in model.participants or []) if name),
                    teachers=tuple(name for name in (_teacher(entry) for entry in model.teachers or []) if name),
                    organization=organizations.get(str(model.id)),
                )
            )
        return performances

    @staticmethod
    def _applicants(models: list[SubmissionModel]) -> dict[str, dict[str, str]]:
        """Applicant id → the account's email and display name, in one query.

        The address a results letter goes to. An applicant whose account has since been
        erased simply has no entry, and the letter is counted as skipped rather than sent
        to a guessed address.
        """
        ids = {str(model.applicant_id) for model in models}
        if not ids:
            return {}
        rows = UserModel.objects.filter(id__in=list(ids), deleted_at__isnull=True).values("id", "email", "first_name", "last_name")
        resolved: dict[str, dict[str, str]] = {}
        for row in rows:
            name = " ".join(part for part in (_clean(row["first_name"]), _clean(row["last_name"])) if part)
            resolved[str(row["id"])] = {"email": str(row["email"] or ""), "name": name}
        return resolved

    @staticmethod
    def _taxonomy(models: list[SubmissionModel]) -> dict[str, dict[str, str]]:
        """One id→name map per taxonomy axis, built from one query each."""
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
        """Submission id → the lead participant's educational organization.

        Normally the registry's: the link is the ``registry_participant_id`` a
        submission denormalizes, resolved through the Participants context in a single
        query for the whole batch. An entry whose institution an organizer corrected
        carries that correction on the participant row itself and is answered from
        there without a lookup.
        """
        pinned_by_submission: dict[str, str] = {}
        registry_by_submission: dict[str, str] = {}
        for model in models:
            for entry in model.participants or []:
                # An institution the organizer corrected on the entry itself wins over
                # the registry, and only for this entry: that is what the correction
                # asked for. Absent — the ordinary case, and the case for every entry
                # submitted before the field existed — the registry answers as before.
                pinned = _clean(entry.get("organization_name"))
                if pinned:
                    pinned_by_submission[str(model.id)] = pinned
                    break
                registry_id = _clean(entry.get("registry_participant_id"))
                if registry_id:
                    registry_by_submission[str(model.id)] = registry_id
                    break
        if not registry_by_submission:
            return pinned_by_submission
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
        resolved = {
            submission_id: by_participant[registry_id]
            for submission_id, registry_id in registry_by_submission.items()
            if registry_id in by_participant
        }
        resolved.update(pinned_by_submission)
        return resolved
