"""Flat, framework-free read views and commands for the Platform context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.platform.domain.entities import PlatformAdministrator

__all__ = ["GrantPlatformAdministratorCommand", "PlatformAdministratorView", "RevokePlatformAdministratorCommand"]


@dataclass(frozen=True, slots=True)
class GrantPlatformAdministratorCommand:
    """Grant platform-operator access to an existing account (by its Identity id)."""

    user_id: str


@dataclass(frozen=True, slots=True)
class RevokePlatformAdministratorCommand:
    """Withdraw platform-operator access from an account."""

    user_id: str


@dataclass(frozen=True, slots=True)
class PlatformAdministratorView:
    """A flat read view of one administrator grant."""

    id: str
    user_id: str
    granted_at: datetime
    revoked_at: datetime | None
    is_active: bool

    @classmethod
    def from_administrator(cls, administrator: PlatformAdministrator) -> PlatformAdministratorView:
        return cls(
            id=administrator.id.json(),
            user_id=administrator.user_id.json(),
            granted_at=administrator.granted_at,
            revoked_at=administrator.revoked_at,
            is_active=administrator.is_active(),
        )
