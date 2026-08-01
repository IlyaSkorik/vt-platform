"""Use cases for platform-operator access.

Three of them, all reached from the management command rather than from HTTP:
granting access, withdrawing it, and listing who holds it. There is deliberately
no API that hands out platform access — the only way in is a command run by
whoever administers the deployment.
"""

from __future__ import annotations

from apps.platform.application.dto import (
    GrantPlatformAdministratorCommand,
    PlatformAdministratorView,
    RevokePlatformAdministratorCommand,
)
from apps.platform.application.exceptions import PlatformAdministratorNotFoundError
from apps.platform.application.interfaces import (
    Clock,
    PlatformAdministratorRepository,
    UuidGenerator,
)
from apps.platform.domain.entities import PlatformAdministrator
from apps.platform.domain.value_objects import PlatformAdministratorId, PlatformUserId

__all__ = [
    "GrantPlatformAdministratorHandler",
    "ListPlatformAdministratorsHandler",
    "RevokePlatformAdministratorHandler",
]


class GrantPlatformAdministratorHandler:
    """Use case: give an existing account platform-operator access.

    Idempotent by design, and re-granting a withdrawn access restores the original
    record rather than issuing a second one: an account has at most one grant, so
    "who can see across every organization" is always one row per person.
    """

    def __init__(
        self,
        *,
        administrators: PlatformAdministratorRepository,
        clock: Clock,
        uuids: UuidGenerator,
    ) -> None:
        self._administrators = administrators
        self._clock = clock
        self._uuids = uuids

    def handle(self, command: GrantPlatformAdministratorCommand) -> PlatformAdministratorView:
        now = self._clock.utcnow()
        user_id = PlatformUserId.from_string(command.user_id)

        existing = self._administrators.find_by_user(user_id)
        if existing is not None:
            if not existing.is_active():
                existing.regrant(now=now)
                self._administrators.save(existing)
            return PlatformAdministratorView.from_administrator(existing)

        administrator = PlatformAdministrator.grant(
            administrator_id=PlatformAdministratorId.from_uuid(self._uuids.new()),
            user_id=user_id,
            now=now,
        )
        self._administrators.save(administrator)
        return PlatformAdministratorView.from_administrator(administrator)


class RevokePlatformAdministratorHandler:
    """Use case: withdraw platform-operator access from an account."""

    def __init__(self, *, administrators: PlatformAdministratorRepository, clock: Clock) -> None:
        self._administrators = administrators
        self._clock = clock

    def handle(self, command: RevokePlatformAdministratorCommand) -> PlatformAdministratorView:
        now = self._clock.utcnow()
        user_id = PlatformUserId.from_string(command.user_id)
        administrator = self._administrators.find_by_user(user_id)
        if administrator is None:
            raise PlatformAdministratorNotFoundError(f"No platform administrator grant for user {command.user_id}.")
        if administrator.is_active():
            administrator.revoke(now=now)
            self._administrators.save(administrator)
        return PlatformAdministratorView.from_administrator(administrator)


class ListPlatformAdministratorsHandler:
    """Use case: list every grant ever issued, revoked ones included."""

    def __init__(self, *, administrators: PlatformAdministratorRepository) -> None:
        self._administrators = administrators

    def handle(self) -> list[PlatformAdministratorView]:
        return [PlatformAdministratorView.from_administrator(row) for row in self._administrators.list_all()]
