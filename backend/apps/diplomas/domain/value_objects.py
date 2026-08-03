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

#: A decoded JSON object as it arrives from the persistence layer.
#:
#: ``object`` rather than ``Any``: the domain layer bans explicit ``Any`` (mypy.ini),
#: and here the ban earns its keep. These snapshots are read back out of a JSON
#: column that may have been written by an older revision of this file, so the code
#: genuinely does not know the shape and must narrow every read. With ``Any`` the
#: helpers below type-checked while silently trusting whatever was in the column.
type JsonDict = dict[str, object]

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


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _mapping(value: object) -> JsonDict:
    """Narrow a nested JSON value to an object, treating anything else as absent.

    A snapshot that has lost a whole sub-object prints with that section blank,
    which is what a missing key already did — better than raising while rendering
    a diploma that has already been issued.
    """
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _rows(value: object) -> list[JsonDict]:
    """Narrow a nested JSON array of objects, treating anything else as empty."""
    if not isinstance(value, list):
        return []
    return [_mapping(row) for row in value]


def _age(value: object) -> int | None:
    """Narrow a stored age. Anything that is not a whole number reads as unknown.

    Age is printed, never computed with, and a diploma is routinely created before
    it is known — so an unparseable value means "do not print an age", not an error.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


@dataclass(frozen=True, slots=True)
class ParticipantSnapshot:
    """The performer as printed: a single display name and, if known, age."""

    display_name: str
    age: int | None = None

    def to_dict(self) -> JsonDict:
        return {"display_name": self.display_name, "age": self.age}

    @classmethod
    def from_dict(cls, data: JsonDict) -> ParticipantSnapshot:
        return cls(display_name=str(data.get("display_name") or ""), age=_age(data.get("age")))


@dataclass(frozen=True, slots=True)
class TeacherSnapshot:
    """One teacher on the diploma: full name and role label."""

    name: str
    role: str | None = None

    def to_dict(self) -> JsonDict:
        return {"name": self.name, "role": self.role}

    @classmethod
    def from_dict(cls, data: JsonDict) -> TeacherSnapshot:
        return cls(name=str(data.get("name") or ""), role=_clean(data.get("role")))


@dataclass(frozen=True, slots=True)
class OrganizationSnapshot:
    """The participant's educational organization, if any."""

    name: str | None = None

    def to_dict(self) -> JsonDict:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: JsonDict) -> OrganizationSnapshot:
        return cls(name=_clean(data.get("name")))


@dataclass(frozen=True, slots=True)
class NominationSnapshot:
    """The nomination axes, resolved to their labels at creation time."""

    title: str | None = None
    discipline: str | None = None
    participant_group: str | None = None
    age_category: str | None = None

    def to_dict(self) -> JsonDict:
        return {
            "title": self.title,
            "discipline": self.discipline,
            "participant_group": self.participant_group,
            "age_category": self.age_category,
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> NominationSnapshot:
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

    def to_dict(self) -> JsonDict:
        return {"title": self.title}

    @classmethod
    def from_dict(cls, data: JsonDict) -> PerformanceSnapshot:
        return cls(title=_clean(data.get("title")))


@dataclass(frozen=True, slots=True)
class CompetitionSnapshot:
    """The competition, frozen: title, date and city as printed."""

    title: str | None = None
    date: str | None = None
    city: str | None = None

    def to_dict(self) -> JsonDict:
        return {"title": self.title, "date": self.date, "city": self.city}

    @classmethod
    def from_dict(cls, data: JsonDict) -> CompetitionSnapshot:
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

    def to_dict(self) -> JsonDict:
        return {"degree": self.degree}

    @classmethod
    def from_dict(cls, data: JsonDict) -> AwardSnapshot:
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

    def to_dict(self) -> JsonDict:
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
    def from_dict(cls, data: JsonDict) -> DiplomaSnapshot:
        return cls(
            participant=ParticipantSnapshot.from_dict(_mapping(data.get("participant"))),
            teachers=tuple(TeacherSnapshot.from_dict(row) for row in _rows(data.get("teachers"))),
            organization=OrganizationSnapshot.from_dict(_mapping(data.get("organization"))),
            nomination=NominationSnapshot.from_dict(_mapping(data.get("nomination"))),
            performance=PerformanceSnapshot.from_dict(_mapping(data.get("performance"))),
            competition=CompetitionSnapshot.from_dict(_mapping(data.get("competition"))),
            award=AwardSnapshot.from_dict(_mapping(data.get("award"))),
        )
