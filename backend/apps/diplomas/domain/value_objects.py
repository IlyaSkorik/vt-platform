"""Value objects for the Diplomas bounded context.

Framework-free (no Django imports). These types describe a diploma's immutable
snapshot and lifecycle. The snapshot is the crux of the aggregate: a diploma
freezes the data it was created from, so later edits to the submission or the
competition never change an already-created diploma.

There is deliberately **no "place"** concept — a result is only ``award.degree``
(e.g. "Гран-при", "Лауреат I степени", "Участник"), which may be ``None`` until
the jury has sat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "AwardSnapshot",
    "CompetitionSnapshot",
    "DiplomaSnapshot",
    "DiplomaStatus",
    "NominationSnapshot",
    "OrganizationSnapshot",
    "ParticipantSnapshot",
    "PerformanceSnapshot",
    "TeacherSnapshot",
]


class DiplomaStatus(Enum):
    """Lifecycle of a diploma.

    ``DRAFT``     — created, data snapshotted, no PDF yet.
    ``GENERATED`` — a PDF has been produced (future stage).
    ``ISSUED``    — handed to the participant / published (future stage).
    ``CANCELLED`` — voided (future stage).
    """

    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class ParticipantSnapshot:
    """The performer as printed: a single display name and, if known, age."""

    display_name: str
    age: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"display_name": self.display_name, "age": self.age}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParticipantSnapshot:
        age = data.get("age")
        return cls(display_name=str(data.get("display_name") or ""), age=int(age) if age is not None else None)


@dataclass(frozen=True, slots=True)
class TeacherSnapshot:
    """One teacher on the diploma: full name and role label."""

    name: str
    role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "role": self.role}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeacherSnapshot:
        return cls(name=str(data.get("name") or ""), role=_clean(data.get("role")))


@dataclass(frozen=True, slots=True)
class OrganizationSnapshot:
    """The participant's educational organization, if any."""

    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrganizationSnapshot:
        return cls(name=_clean(data.get("name")))


@dataclass(frozen=True, slots=True)
class NominationSnapshot:
    """The nomination axes, resolved to their labels at creation time."""

    title: str | None = None
    discipline: str | None = None
    participant_group: str | None = None
    age_category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "discipline": self.discipline,
            "participant_group": self.participant_group,
            "age_category": self.age_category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NominationSnapshot:
        return cls(
            title=_clean(data.get("title")),
            discipline=_clean(data.get("discipline")),
            participant_group=_clean(data.get("participant_group")),
            age_category=_clean(data.get("age_category")),
        )


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """The performed work."""

    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceSnapshot:
        return cls(title=_clean(data.get("title")))


@dataclass(frozen=True, slots=True)
class CompetitionSnapshot:
    """The competition, frozen: title, date and city as printed."""

    title: str | None = None
    date: str | None = None
    city: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "date": self.date, "city": self.city}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompetitionSnapshot:
        return cls(
            title=_clean(data.get("title")),
            date=_clean(data.get("date")),
            city=_clean(data.get("city")),
        )


@dataclass(frozen=True, slots=True)
class AwardSnapshot:
    """The result. Only a degree — there is no "place". ``None`` until the jury
    has decided (a diploma is routinely created before the degree is known)."""

    degree: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"degree": self.degree}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AwardSnapshot:
        return cls(degree=_clean(data.get("degree")))


@dataclass(frozen=True, slots=True)
class DiplomaSnapshot:
    """The whole frozen dataset a diploma is printed from.

    Self-contained by design: it holds resolved *values*, never ids or references
    back into other contexts, so nothing that changes later can alter it.
    """

    participant: ParticipantSnapshot
    teachers: tuple[TeacherSnapshot, ...] = ()
    organization: OrganizationSnapshot = field(default_factory=OrganizationSnapshot)
    nomination: NominationSnapshot = field(default_factory=NominationSnapshot)
    performance: PerformanceSnapshot = field(default_factory=PerformanceSnapshot)
    competition: CompetitionSnapshot = field(default_factory=CompetitionSnapshot)
    award: AwardSnapshot = field(default_factory=AwardSnapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant": self.participant.to_dict(),
            "teachers": [teacher.to_dict() for teacher in self.teachers],
            "organization": self.organization.to_dict(),
            "nomination": self.nomination.to_dict(),
            "performance": self.performance.to_dict(),
            "competition": self.competition.to_dict(),
            "award": self.award.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiplomaSnapshot:
        return cls(
            participant=ParticipantSnapshot.from_dict(data.get("participant") or {}),
            teachers=tuple(TeacherSnapshot.from_dict(row) for row in data.get("teachers") or []),
            organization=OrganizationSnapshot.from_dict(data.get("organization") or {}),
            nomination=NominationSnapshot.from_dict(data.get("nomination") or {}),
            performance=PerformanceSnapshot.from_dict(data.get("performance") or {}),
            competition=CompetitionSnapshot.from_dict(data.get("competition") or {}),
            award=AwardSnapshot.from_dict(data.get("award") or {}),
        )
