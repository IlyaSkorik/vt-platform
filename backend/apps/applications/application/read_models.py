"""Organizer-facing **Participant Registry** read model (a projection port).

The registry is *not* an aggregate and owns *no* storage of its own. It is a
read-only **projection** derived on demand from the Application/Submission
bounded context (the single source of truth): every participant the organizer
sees is reconstructed from the ``participants`` embedded in the submissions that
reached a *confirmed* lifecycle state. Because it is computed on read, the
registry is always consistent with the underlying applications — there is no
duplicated table to keep in sync (ARCH-001 §7.2, DATA-001).

This module defines only the **port** (a ``Protocol``) and the flat, framework
-free ``@dataclass`` views the presentation edge renders. The concrete Django
adapter that queries the ORM lives in
``apps.applications.infrastructure.read_models`` and is assembled at the
composition root, so the presentation layer depends on this abstraction rather
than on persistence details (Dependency Inversion, ARCH-001 §7.3).

Confidentiality (ARCH-001 §21.6): an organizer may only ever see participation
that happened inside *their own organization's* competitions. The projection is
therefore always scoped to the organization's competition set — never to a
child's global history. The platform currently runs a single organization, so
"the organization's competitions" is every competition today; the scoping seam
(:meth:`OrganizerParticipantRegistry.list`/``get`` taking the competition set)
is where per-organization narrowing plugs in once multi-tenancy exists.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

__all__ = [
    "OrganizerParticipantRegistry",
    "RegistryApplicationView",
    "RegistryAwardView",
    "RegistryDocumentView",
    "RegistryFilters",
    "RegistryHistoryEntry",
    "RegistryNoteView",
    "RegistryOrganizationView",
    "RegistryParticipantDetail",
    "RegistryParticipantSummary",
    "RegistryPerformanceView",
    "RegistryTeacherView",
]


@dataclass(frozen=True, slots=True)
class RegistryFilters:
    """Server-side narrowing of the participant list (all optional).

    Everything is applied by the backend — the frontend computes nothing. A
    ``None``/empty field is simply not applied.
    """

    query: str | None = None
    gender: str | None = None
    age_min: int | None = None
    age_max: int | None = None
    competition_id: str | None = None
    organization: str | None = None
    participant_type: str | None = None
    has_documents: bool | None = None


@dataclass(frozen=True, slots=True)
class RegistryOrganizationView:
    """An educational organization a participant applied under (name snapshot)."""

    id: str | None
    name: str


@dataclass(frozen=True, slots=True)
class RegistryTeacherView:
    """A teacher who prepared the participant, as recorded on the submission."""

    name: str
    role: str


@dataclass(frozen=True, slots=True)
class RegistryApplicationView:
    """One submission the participant appears in, inside this organization."""

    submission_id: str
    application_id: str | None
    competition_id: str
    competition: str
    status: str
    performance_title: str | None
    organization: str | None
    teachers: tuple[RegistryTeacherView, ...]
    submitted_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class RegistryPerformanceView:
    """A competitive act (one per submission) the participant performed."""

    submission_id: str
    competition_id: str
    competition: str
    status: str
    title: str
    duration_seconds: int | None
    nomination: str | None
    discipline: str | None
    age_category: str | None
    participant_group: str | None
    participation_format: str | None
    comment: str | None


@dataclass(frozen=True, slots=True)
class RegistryDocumentView:
    """A file uploaded within one of the participant's submissions."""

    id: str
    submission_id: str
    competition: str
    type: str
    file: str
    caption: str | None


@dataclass(frozen=True, slots=True)
class RegistryHistoryEntry:
    """A single participation event in this organization's competitions."""

    submission_id: str
    competition_id: str
    competition: str
    status: str
    date: str


@dataclass(frozen=True, slots=True)
class RegistryNoteView:
    """An internal organizer note recorded against one of the submissions."""

    submission_id: str
    competition: str
    text: str
    created_at: str | None


@dataclass(frozen=True, slots=True)
class RegistryAwardView:
    """A participant award.

    Reserved contract: awards/results are owned by the Results/Judging contexts,
    which are not yet implemented. The projection therefore never yields awards
    today — the field exists so the API shape is stable when a source appears.
    """

    title: str
    competition: str
    date: str | None


@dataclass(frozen=True, slots=True)
class RegistryParticipantSummary:
    """The dense-table row: identity + aggregate counts, no heavy detail."""

    key: str
    participant_type: str
    display_name: str
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    full_name: str
    birth_date: str | None
    age: int | None
    gender: str | None
    member_count: int
    primary_organization: RegistryOrganizationView | None
    organizations: tuple[RegistryOrganizationView, ...]
    teachers: tuple[RegistryTeacherView, ...]
    competitions_count: int
    applications_count: int
    performances_count: int
    documents_count: int
    last_activity: str


@dataclass(frozen=True, slots=True)
class RegistryParticipantDetail:
    """The full participant card: the summary plus every related collection."""

    summary: RegistryParticipantSummary
    applications: tuple[RegistryApplicationView, ...]
    performances: tuple[RegistryPerformanceView, ...]
    documents: tuple[RegistryDocumentView, ...]
    history: tuple[RegistryHistoryEntry, ...]
    notes: tuple[RegistryNoteView, ...]
    awards: tuple[RegistryAwardView, ...] = field(default_factory=tuple)


@runtime_checkable
class OrganizerParticipantRegistry(Protocol):
    """Port: project the organizer's participant registry from submissions.

    ``competition_ids`` is the confidentiality scope — the organization's own
    competition set. Implementations must never read participation outside it.
    """

    def list(
        self,
        *,
        competition_ids: Sequence[str],
        filters: RegistryFilters,
    ) -> list[RegistryParticipantSummary]:
        """Return the matching participant summaries (already filtered/sorted)."""
        ...

    def get(
        self,
        *,
        competition_ids: Sequence[str],
        key: str,
    ) -> RegistryParticipantDetail | None:
        """Return the full card for ``key``, or ``None`` if absent from scope."""
        ...
