"""Django adapter for the organizer :mod:`Participant Registry read model
<apps.applications.application.read_models>`.

Projects participants on demand from ``SubmissionModel`` rows (the source of
truth) — no dedicated table, so the registry can never drift from the
applications it is derived from. Participants are grouped across submissions by
their ``registry_participant_id`` when present (the stable cross-submission
identity denormalized from the applicant's registry); a submission-local
identity is used as a fallback when a submission carries no registry link.

Only submissions in a *confirmed* lifecycle state
(:data:`_CONFIRMED_STATUSES`) contribute — a participant enters the organizer's
registry once their participation is confirmed, exactly as the queue view treats
those states as "in the competition".

The adapter reads sibling ORM models it is allowed to (same context:
``SubmissionModel``/``ApplicationModel``; the Competitions context's read tables
for name resolution, mirroring the organizer processing view). It never mutates
anything.
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from apps.applications.application.read_models import (
    RegistryApplicationView,
    RegistryDocumentView,
    RegistryFilters,
    RegistryHistoryEntry,
    RegistryNoteView,
    RegistryOrganizationView,
    RegistryParticipantDetail,
    RegistryParticipantSummary,
    RegistryPerformanceView,
    RegistryTeacherView,
)
from apps.applications.infrastructure.models.application import ApplicationModel
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

__all__ = ["DjangoOrganizerParticipantRegistry"]

#: Submission states that mean "confirmed participant" — everything from
#: acceptance onward (see ``SubmissionStatus``). Draft/submitted/under-review
#: applications are *not* yet participants of the organization.
_CONFIRMED_STATUSES: tuple[str, ...] = ("ACCEPTED", "PAID", "SCHEDULED", "COMPLETED")


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat().replace("+00:00", "Z")


def _age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _parse_birth_date(raw: object | None) -> date | None:
    text = _clean(raw)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _person_full_name(last: str | None, first: str | None, middle: str | None) -> str:
    return " ".join(part for part in (last, first, middle) if part)


def _teacher_name(entry: dict[str, Any]) -> str:
    return _person_full_name(
        _clean(entry.get("last_name")),
        _clean(entry.get("first_name")),
        _clean(entry.get("middle_name")),
    )


@dataclass
class _Accumulator:
    """Mutable grouping bucket for one participant across many submissions."""

    key: str
    display_name: str = ""
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    member_count: int = 1
    identity_stamp: datetime | None = None
    organizations: dict[str, RegistryOrganizationView] = field(default_factory=dict)
    primary_org_key: str | None = None
    teachers: dict[str, RegistryTeacherView] = field(default_factory=dict)
    applications: list[RegistryApplicationView] = field(default_factory=list)
    performances: list[RegistryPerformanceView] = field(default_factory=list)
    documents: list[RegistryDocumentView] = field(default_factory=list)
    history: list[RegistryHistoryEntry] = field(default_factory=list)
    notes: list[RegistryNoteView] = field(default_factory=list)
    competition_ids: set[str] = field(default_factory=set)
    last_activity: datetime | None = None

    def note_identity(self, *, updated_at: datetime | None, participant: dict[str, Any]) -> None:
        """Adopt name/birth/gender from the most recently updated submission."""
        if self.identity_stamp is not None and updated_at is not None and updated_at <= self.identity_stamp:
            return
        self.identity_stamp = updated_at or self.identity_stamp
        self.display_name = _clean(participant.get("display_name")) or self.display_name
        self.first_name = _clean(participant.get("first_name")) or self.first_name
        self.last_name = _clean(participant.get("last_name")) or self.last_name
        self.middle_name = _clean(participant.get("middle_name")) or self.middle_name
        birth = _parse_birth_date(participant.get("birth_date"))
        if birth is not None:
            self.birth_date = birth
        gender = _clean(participant.get("gender"))
        if gender is not None:
            self.gender = gender
        with contextlib.suppress(TypeError, ValueError):
            self.member_count = max(self.member_count, int(participant.get("member_count", 1)))


class DjangoOrganizerParticipantRegistry:
    """Concrete :class:`OrganizerParticipantRegistry` over Django ORM reads."""

    def list(
        self,
        *,
        competition_ids: Sequence[str],
        filters: RegistryFilters,
    ) -> list[RegistryParticipantSummary]:
        # A competition filter narrows the projection *scope* (who appears),
        # while the detail card always shows the participant's full history
        # across the organization — so ``get`` keeps the unnarrowed scope.
        scope: Sequence[str] = competition_ids
        if filters.competition_id:
            scope = [cid for cid in competition_ids if cid == filters.competition_id]
        accumulators = self._project(scope)
        summaries = [self._summarize(acc) for acc in accumulators.values()]
        summaries = [s for s in summaries if _matches(s, filters)]
        summaries.sort(key=lambda s: (s.full_name.lower(), s.key))
        return summaries

    def get(
        self,
        *,
        competition_ids: Sequence[str],
        key: str,
    ) -> RegistryParticipantDetail | None:
        accumulators = self._project(competition_ids)
        acc = accumulators.get(key)
        if acc is None:
            return None
        summary = self._summarize(acc)
        applications = sorted(acc.applications, key=lambda a: a.updated_at, reverse=True)
        performances = sorted(acc.performances, key=lambda p: p.submission_id)
        history = sorted(acc.history, key=lambda h: h.date, reverse=True)
        notes = sorted(acc.notes, key=lambda n: n.created_at or "", reverse=True)
        return RegistryParticipantDetail(
            summary=summary,
            applications=tuple(applications),
            performances=tuple(performances),
            documents=tuple(acc.documents),
            history=tuple(history),
            notes=tuple(notes),
            awards=(),
        )

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def _project(self, competition_ids: Sequence[str]) -> dict[str, _Accumulator]:
        scope = list(competition_ids)
        if not scope:
            return {}

        competition_name = {
            str(row["id"]): str(row["title"])
            for row in CompetitionModel.objects.filter(
                deleted_at__isnull=True, id__in=scope
            ).values("id", "title")
        }
        taxonomy = self._taxonomy_names(scope)
        application_id_by_submission = self._application_ids_by_submission()

        submissions = SubmissionModel.objects.filter(
            deleted_at__isnull=True,
            competition_id__in=scope,
            status__in=_CONFIRMED_STATUSES,
        ).order_by("updated_at")

        accumulators: dict[str, _Accumulator] = {}
        for model in submissions:
            competition_id = str(model.competition_id)
            competition = competition_name.get(competition_id, "—")
            performance = model.performance or {}
            teachers = [
                RegistryTeacherView(name=name, role=str(entry.get("role") or ""))
                for entry in (model.teachers or [])
                if (name := _teacher_name(entry))
            ]
            application_id = application_id_by_submission.get(str(model.id))
            submitted_at = _iso(model.created_at)
            updated_at = _iso(model.updated_at)

            for participant in model.participants or []:
                key = self._identity_key(participant, submission_id=str(model.id))
                acc = accumulators.get(key)
                if acc is None:
                    acc = _Accumulator(key=key)
                    accumulators[key] = acc
                acc.note_identity(updated_at=model.updated_at, participant=participant)
                acc.competition_ids.add(competition_id)
                if acc.last_activity is None or (
                    model.updated_at is not None and model.updated_at > acc.last_activity
                ):
                    acc.last_activity = model.updated_at
                for teacher in teachers:
                    acc.teachers.setdefault(f"{teacher.name}|{teacher.role}", teacher)
                acc.applications.append(
                    RegistryApplicationView(
                        submission_id=str(model.id),
                        application_id=application_id,
                        competition_id=competition_id,
                        competition=competition,
                        status=model.status,
                        performance_title=_clean(performance.get("title")),
                        organization=None,
                        teachers=tuple(teachers),
                        submitted_at=submitted_at,
                        updated_at=updated_at,
                    )
                )
                if performance:
                    acc.performances.append(
                        RegistryPerformanceView(
                            submission_id=str(model.id),
                            competition_id=competition_id,
                            competition=competition,
                            status=model.status,
                            title=str(performance.get("title") or ""),
                            duration_seconds=performance.get("duration_seconds"),
                            nomination=taxonomy["nomination"].get(str(performance.get("nomination_id") or "")),
                            discipline=taxonomy["discipline"].get(str(performance.get("discipline_id") or "")),
                            age_category=taxonomy["age_category"].get(str(performance.get("age_category_id") or "")),
                            participant_group=taxonomy["participant_group"].get(
                                str(performance.get("participant_group_id") or "")
                            ),
                            participation_format=taxonomy["participation_format"].get(
                                str(performance.get("participation_format_id") or "")
                            ),
                            comment=_clean(performance.get("comment")),
                        )
                    )
                for attachment in model.attachments or []:
                    acc.documents.append(
                        RegistryDocumentView(
                            id=str(attachment.get("id") or ""),
                            submission_id=str(model.id),
                            competition=competition,
                            type=str(attachment.get("type") or ""),
                            file=str(attachment.get("file") or ""),
                            caption=_clean(attachment.get("caption")),
                        )
                    )
                acc.history.append(
                    RegistryHistoryEntry(
                        submission_id=str(model.id),
                        competition_id=competition_id,
                        competition=competition,
                        status=model.status,
                        date=updated_at,
                    )
                )
                for note in model.organizer_notes or []:
                    text = _clean(note.get("text"))
                    if text is None:
                        continue
                    acc.notes.append(
                        RegistryNoteView(
                            submission_id=str(model.id),
                            competition=competition,
                            text=text,
                            created_at=_clean(note.get("created_at")),
                        )
                    )
        self._attach_organizations(accumulators)
        return accumulators

    @staticmethod
    def _attach_organizations(accumulators: dict[str, _Accumulator]) -> None:
        """Resolve each participant's educational organizations from the registry.

        A participant's organization is not carried on the submission or the order
        (that snapshot is unused); it lives in the Participants context, linked to
        the ``registry_participant_id`` the submission denormalizes. We read it here
        for participants that carry a registry link (keys prefixed ``r:``).
        """
        registry_ids: list[uuid.UUID] = []
        for key in accumulators:
            if key.startswith("r:"):
                with contextlib.suppress(ValueError):
                    registry_ids.append(uuid.UUID(key[2:]))
        if not registry_ids:
            return
        memberships = (
            ParticipantOrganizationMembershipModel.objects.filter(
                participant_id__in=registry_ids,
                deleted_at__isnull=True,
                organization__deleted_at__isnull=True,
            )
            .select_related("organization")
            .order_by("-is_primary", "organization__name")
        )
        for membership in memberships:
            acc = accumulators.get(f"r:{membership.participant_id}")
            if acc is None:
                continue
            organization = membership.organization
            view = RegistryOrganizationView(id=str(organization.id), name=organization.name)
            acc.organizations.setdefault(view.id or view.name, view)
            if membership.is_primary and acc.primary_org_key is None:
                acc.primary_org_key = view.id or view.name

    @staticmethod
    def _identity_key(participant: dict[str, Any], *, submission_id: str) -> str:
        registry_id = _clean(participant.get("registry_participant_id"))
        if registry_id is not None:
            return f"r:{registry_id}"
        local_id = _clean(participant.get("id")) or "0"
        return f"s:{submission_id}:{local_id}"

    @staticmethod
    def _taxonomy_names(scope: Sequence[str]) -> dict[str, dict[str, str]]:
        def names(model: Any) -> dict[str, str]:
            return {
                str(row["id"]): str(row["name"])
                for row in model.objects.filter(
                    deleted_at__isnull=True, competition_id__in=scope
                ).values("id", "name")
            }

        return {
            "nomination": names(CategoryModel),
            "discipline": names(DisciplineModel),
            "age_category": names(AgeCategoryModel),
            "participant_group": names(ParticipantGroupModel),
            "participation_format": names(ParticipationFormatModel),
        }

    @staticmethod
    def _application_ids_by_submission() -> dict[str, str | None]:
        """Map each submission to its owning application (order) id, for deep links."""
        mapping: dict[str, str | None] = {}
        rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values("id", "submission_refs")
        for row in rows:
            application_id = str(row.get("id") or "") or None
            for ref in row.get("submission_refs") or []:
                submission_id = _clean(ref.get("submission_id"))
                if submission_id is not None:
                    mapping[submission_id] = application_id
        return mapping

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize(acc: _Accumulator) -> RegistryParticipantSummary:
        is_collective = acc.member_count > 1 or (acc.first_name is None and acc.last_name is None)
        participant_type = "collective" if is_collective else "solo"
        full_name = (
            (acc.display_name or "Коллектив")
            if is_collective
            else (_person_full_name(acc.last_name, acc.first_name, acc.middle_name) or acc.display_name or "—")
        )
        organizations = tuple(acc.organizations.values())
        primary = acc.organizations.get(acc.primary_org_key or "")
        if primary is None and organizations:
            primary = organizations[0]
        submission_ids = {app.submission_id for app in acc.applications}
        return RegistryParticipantSummary(
            key=acc.key,
            participant_type=participant_type,
            display_name=acc.display_name or full_name,
            first_name=acc.first_name,
            last_name=acc.last_name,
            middle_name=acc.middle_name,
            full_name=full_name,
            birth_date=acc.birth_date.isoformat() if acc.birth_date is not None else None,
            age=_age(acc.birth_date),
            gender=acc.gender,
            member_count=acc.member_count,
            primary_organization=primary,
            organizations=organizations,
            teachers=tuple(acc.teachers.values()),
            competitions_count=len(acc.competition_ids),
            applications_count=len(submission_ids),
            performances_count=len(acc.performances),
            documents_count=len(acc.documents),
            last_activity=_iso(acc.last_activity),
        )


def _matches(summary: RegistryParticipantSummary, filters: RegistryFilters) -> bool:
    if filters.query:
        needle = filters.query.strip().lower()
        haystack = " ".join(
            part
            for part in (
                summary.full_name,
                summary.display_name,
                summary.primary_organization.name if summary.primary_organization else "",
                " ".join(org.name for org in summary.organizations),
                " ".join(t.name for t in summary.teachers),
            )
            if part
        ).lower()
        if needle not in haystack:
            return False
    if filters.gender and summary.gender != filters.gender:
        return False
    if filters.participant_type and summary.participant_type != filters.participant_type:
        return False
    if filters.age_min is not None and (summary.age is None or summary.age < filters.age_min):
        return False
    if filters.age_max is not None and (summary.age is None or summary.age > filters.age_max):
        return False
    if filters.organization:
        org_needle = filters.organization.strip().lower()
        if not any(org_needle in org.name.lower() for org in summary.organizations):
            return False
    return not (
        filters.has_documents is not None
        and (summary.documents_count > 0) != filters.has_documents
    )
