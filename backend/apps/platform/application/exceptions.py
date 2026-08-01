"""Application-layer exceptions for the Platform bounded context."""

from __future__ import annotations

from typing import ClassVar

__all__ = ["ApplicationError", "PlatformAdministratorNotFoundError"]


class ApplicationError(Exception):
    """Base class for every error the Platform application layer raises."""

    code: ClassVar[str] = "platform_error"


class PlatformAdministratorNotFoundError(ApplicationError):
    """No administrator grant exists for the account named."""

    code: ClassVar[str] = "platform_administrator_not_found"
