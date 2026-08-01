"""Composition root for the Platform bounded context.

The one place framework-free use cases are wired to their concrete adapters
(ARCH-001 §7.3). Callers — the management commands, the platform API views, the
``/users/me`` composition edge — ask here for an assembled handler or read
service and stay ignorant of which repository or clock sits behind it.
"""

from __future__ import annotations

from apps.platform.application.handlers import (
    GrantPlatformAdministratorHandler,
    ListPlatformAdministratorsHandler,
    RevokePlatformAdministratorHandler,
)
from apps.platform.application.read_models import PlatformAccessReader
from apps.platform.infrastructure.repositories import DjangoPlatformAdministratorRepository
from apps.platform.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_grant_platform_administrator_handler",
    "build_list_platform_administrators_handler",
    "build_platform_access_read_service",
    "build_revoke_platform_administrator_handler",
]


def build_grant_platform_administrator_handler() -> GrantPlatformAdministratorHandler:
    return GrantPlatformAdministratorHandler(
        administrators=DjangoPlatformAdministratorRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
    )


def build_revoke_platform_administrator_handler() -> RevokePlatformAdministratorHandler:
    return RevokePlatformAdministratorHandler(
        administrators=DjangoPlatformAdministratorRepository(),
        clock=SystemClock(),
    )


def build_list_platform_administrators_handler() -> ListPlatformAdministratorsHandler:
    return ListPlatformAdministratorsHandler(administrators=DjangoPlatformAdministratorRepository())


def build_platform_access_read_service() -> PlatformAccessReader:
    """Assemble the published cross-context platform-access read model."""
    return PlatformAccessReader(administrators=DjangoPlatformAdministratorRepository())
