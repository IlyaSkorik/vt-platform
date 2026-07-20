"""Composition root for Identity cross-context read models.

The place other bounded contexts reach for a fully-assembled Identity read
service and stay ignorant of *which* adapter sits behind the port (ARCH-001
§7.3). Kept separate from the authentication-edge composition
(``presentation/api/v1/auth/composition.py``, which wires the write-side use
cases) so a consuming context imports only the read seam it needs.

Every adapter is stateless and cheap to build, so services are assembled per
call; there is no shared mutable state.
"""

from __future__ import annotations

from apps.identity.infrastructure.read_models import DjangoUserDirectory

__all__ = ["build_user_directory"]


def build_user_directory() -> DjangoUserDirectory:
    """Assemble the published cross-context user directory read model."""
    return DjangoUserDirectory()
