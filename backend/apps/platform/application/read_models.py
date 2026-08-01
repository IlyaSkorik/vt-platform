"""The published cross-context read model of platform-operator access.

:class:`PlatformAccessReadService` is the only seam other contexts (and the
``/users/me`` composition edge) use to ask "does this account operate the
platform?". Consumers depend on the port and get a boolean — they never import a
Platform aggregate or repository (ARCH-001 §14).
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from apps.platform.application.interfaces import PlatformAdministratorRepository
from apps.platform.domain.value_objects import PlatformUserId

__all__ = ["PlatformAccessReadService", "PlatformAccessReader"]


@runtime_checkable
class PlatformAccessReadService(Protocol):
    """Port: answer "is this user a platform administrator?" for other contexts."""

    def is_platform_administrator(self, user_id: uuid.UUID) -> bool: ...


class PlatformAccessReader:
    """Concrete :class:`PlatformAccessReadService` over the Platform repository.

    A malformed id simply means "no" rather than an error: this is consulted on
    every ``/users/me`` call and on every platform-gated request, where absence of
    access is the ordinary answer.
    """

    def __init__(self, *, administrators: PlatformAdministratorRepository) -> None:
        self._administrators = administrators

    def is_platform_administrator(self, user_id: uuid.UUID) -> bool:
        try:
            platform_user_id = PlatformUserId.from_uuid(user_id)
        except ValueError:
            return False
        administrator = self._administrators.find_by_user(platform_user_id)
        return administrator is not None and administrator.is_active()
