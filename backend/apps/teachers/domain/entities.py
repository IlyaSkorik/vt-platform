"""Domain entities for the Teacher Directory bounded context.

One aggregate - the :class:`Teacher` - representing **one entry in a user's personal
directory of mentors**. A teacher belongs to the authenticated user (the
:class:`~apps.teachers.domain.value_objects.OwnerId`); it is deliberately *not*
owned by a competition, a participant, or an application. When a teacher is credited
on a competition submission, the submission snapshots the teacher's details into its
own child entity, so this directory stays a reusable, decoupled source of record.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only - no Django, no
ORM, no clock, no IO. Time is always supplied by the caller (``now``).

Design contract (mirrors the platform's other aggregates):

* **No direct construction.** Build a :class:`Teacher` only via :meth:`Teacher.create`
  or :meth:`Teacher.rehydrate`.
* **Encapsulated state.** All fields private; only read-only views exposed.
* **Behaviour returns events, never publishes them.**
* **Invalid transitions raise** typed errors.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime
from typing import Final

from .events import DomainEvent, TeacherAdded, TeacherArchived, TeacherReactivated, TeacherUpdated
from .exceptions import (
    DirectConstructionError,
    IllegalTeacherStatusTransitionError,
    TeacherNotEditableError,
)
from .value_objects import (
    ConsentReference,
    EmailAddress,
    OwnerId,
    PersonName,
    PhoneNumber,
    TeacherId,
    TeacherRole,
    TeacherStatus,
)

_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class Teacher:
    """The Teacher aggregate root - one reusable entry in a user's personal directory.

    Owns its identity, its owner reference, its display/contact details and its
    archive lifecycle (``ACTIVE <-> ARCHIVED``). Equality/hashing is by
    :class:`TeacherId`.
    """

    _token: InitVar[object]
    _id: TeacherId
    _owner_id: OwnerId
    _name: PersonName
    _role: TeacherRole
    _status: TeacherStatus
    _created_at: datetime
    _updated_at: datetime
    _email: EmailAddress | None = None
    _phone: PhoneNumber | None = None
    #: The Identity consent that permits holding this adult's details.
    _consent: ConsentReference | None = None
    _archived_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "Teacher must be created via Teacher.create() or Teacher.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        teacher_id: TeacherId,
        owner_id: OwnerId,
        name: PersonName,
        role: TeacherRole,
        now: datetime,
        email: EmailAddress | None = None,
        phone: PhoneNumber | None = None,
        consent: ConsentReference | None = None,
    ) -> tuple[Teacher, list[DomainEvent]]:
        """Create a brand-new ACTIVE directory entry.

        ``consent`` references the teacher's own consent to having their details held,
        obtained by whoever is entering them (LEGAL-001 §5.4). Optional here because the
        aggregate cannot know which flow it is in; the API refuses a creation without it.
        """
        teacher = cls(
            _token=_CREATION_TOKEN,
            _id=teacher_id,
            _owner_id=owner_id,
            _name=name,
            _role=role,
            _status=TeacherStatus.ACTIVE,
            _created_at=now,
            _updated_at=now,
            _email=email,
            _phone=phone,
            _consent=consent,
        )
        return teacher, [TeacherAdded(aggregate_id=teacher_id.value, owner_id=owner_id, role=role)]

    @classmethod
    def rehydrate(
        cls,
        *,
        teacher_id: TeacherId,
        owner_id: OwnerId,
        name: PersonName,
        role: TeacherRole,
        status: TeacherStatus,
        created_at: datetime,
        updated_at: datetime,
        email: EmailAddress | None = None,
        phone: PhoneNumber | None = None,
        consent: ConsentReference | None = None,
        archived_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Teacher:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=teacher_id,
            _owner_id=owner_id,
            _name=name,
            _role=role,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _email=email,
            _phone=phone,
            _consent=consent,
            _archived_at=archived_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Read-only views
    # ------------------------------------------------------------------

    @property
    def id(self) -> TeacherId:
        return self._id

    @property
    def owner_id(self) -> OwnerId:
        return self._owner_id

    @property
    def name(self) -> PersonName:
        return self._name

    @property
    def role(self) -> TeacherRole:
        return self._role

    @property
    def email(self) -> EmailAddress | None:
        return self._email

    @property
    def phone(self) -> PhoneNumber | None:
        return self._phone

    @property
    def consent(self) -> ConsentReference | None:
        """The consent on file for holding this teacher's details, if any."""
        return self._consent

    @property
    def status(self) -> TeacherStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def archived_at(self) -> datetime | None:
        return self._archived_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def is_deleted(self) -> bool:
        return self._deleted_at is not None

    def is_active(self) -> bool:
        return self._status is TeacherStatus.ACTIVE

    def is_archived(self) -> bool:
        return self._status is TeacherStatus.ARCHIVED

    def is_owned_by(self, owner_id: OwnerId) -> bool:
        """Whether this directory entry belongs to ``owner_id``."""
        return self._owner_id == owner_id

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        name: PersonName,
        role: TeacherRole,
        now: datetime,
        email: EmailAddress | None = None,
        phone: PhoneNumber | None = None,
    ) -> list[DomainEvent]:
        """Replace the teacher's display/contact details (only while ACTIVE)."""
        if self._status is not TeacherStatus.ACTIVE:
            raise TeacherNotEditableError("Педагог в архиве — сначала верните его из архива.")
        self._name = name
        self._role = role
        self._email = email
        self._phone = phone
        self._touch(now)
        return [TeacherUpdated(aggregate_id=self._id.value)]

    def archive(self, *, now: datetime) -> list[DomainEvent]:
        """Archive the entry (ACTIVE -> ARCHIVED). Never physically deletes it."""
        if self._status is not TeacherStatus.ACTIVE:
            raise IllegalTeacherStatusTransitionError("В архив можно отправить только активного педагога.")
        self._status = TeacherStatus.ARCHIVED
        self._archived_at = now
        self._touch(now)
        return [TeacherArchived(aggregate_id=self._id.value)]

    def reactivate(self, *, now: datetime) -> list[DomainEvent]:
        """Reactivate an archived entry (ARCHIVED -> ACTIVE)."""
        if self._status is not TeacherStatus.ARCHIVED:
            raise IllegalTeacherStatusTransitionError("Вернуть из архива можно только архивного педагога.")
        self._status = TeacherStatus.ACTIVE
        self._archived_at = None
        self._touch(now)
        return [TeacherReactivated(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Teacher) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Teacher(id={self._id!r}, name={self._name.full_name!r}, role={self._role.value!r}, status={self._status.value!r})"


__all__ = ["Teacher"]
