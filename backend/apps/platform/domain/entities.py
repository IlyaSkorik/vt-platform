"""The ``PlatformAdministrator`` aggregate — who operates the platform itself.

One aggregate root, one consistency boundary. A platform administrator sits
*above* every organization: they connect new organizations, set what each owes
the platform, and read across all of them. This is deliberately **not** a staff
role — an organization's OWNER is the top of that organization, and nothing
inside an organization may promote anyone to the platform level.

There is no public grant path at all. The grant is created by a management
command run against a registered account (``grant_platform_admin --email``), which
is the only sanctioned way in; revoking it is the same, in reverse.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only, time supplied
by the caller.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime
from typing import Final

from .exceptions import (
    AdministratorAlreadyActiveError,
    AdministratorAlreadyRevokedError,
    DirectConstructionError,
)
from .value_objects import PlatformAdministratorId, PlatformUserId

__all__ = ["PlatformAdministrator"]

#: Opaque capability token proving construction went through a factory.
_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class PlatformAdministrator:
    """A standing grant of platform-operator access to one Identity account.

    Lifecycle: granted → (revoked → granted again). A revoked grant is kept rather
    than deleted, so the record of who could see across every organization, and
    until when, survives. Equality/hashing is by :class:`PlatformAdministratorId`.
    """

    _token: InitVar[object]
    _id: PlatformAdministratorId
    _user_id: PlatformUserId
    _granted_at: datetime
    _created_at: datetime
    _updated_at: datetime
    _revoked_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "PlatformAdministrator must be created via PlatformAdministrator.grant() or rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def grant(
        cls,
        *,
        administrator_id: PlatformAdministratorId,
        user_id: PlatformUserId,
        now: datetime,
    ) -> PlatformAdministrator:
        """Grant platform-operator access to an account (the management-command path)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=administrator_id,
            _user_id=user_id,
            _granted_at=now,
            _created_at=now,
            _updated_at=now,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        administrator_id: PlatformAdministratorId,
        user_id: PlatformUserId,
        granted_at: datetime,
        created_at: datetime,
        updated_at: datetime,
        revoked_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> PlatformAdministrator:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=administrator_id,
            _user_id=user_id,
            _granted_at=granted_at,
            _created_at=created_at,
            _updated_at=updated_at,
            _revoked_at=revoked_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> PlatformAdministratorId:
        return self._id

    @property
    def user_id(self) -> PlatformUserId:
        return self._user_id

    @property
    def granted_at(self) -> datetime:
        return self._granted_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    def is_active(self) -> bool:
        """Whether this grant currently confers platform-operator access."""
        return self._revoked_at is None

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def revoke(self, *, now: datetime) -> None:
        """Withdraw the grant, leaving the record of it behind."""
        if self._revoked_at is not None:
            raise AdministratorAlreadyRevokedError("Права администратора уже отозваны.")
        self._revoked_at = now
        self._touch(now)

    def regrant(self, *, now: datetime) -> None:
        """Restore a revoked grant, rather than issuing a second one for the same account."""
        if self._revoked_at is None:
            raise AdministratorAlreadyActiveError("Права администратора уже выданы.")
        self._revoked_at = None
        self._granted_at = now
        self._touch(now)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PlatformAdministrator) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"PlatformAdministrator(id={self._id!r}, user_id={self._user_id!r}, active={self.is_active()})"
