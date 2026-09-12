"""Cache adapters for the Organization bounded context.

Concrete implementations of framework-free cache ports declared in the application
layer. The only component here that knows about Django's cache framework.
"""

from __future__ import annotations

import uuid

from django.core.cache import cache

__all__ = ["DjangoModuleCache"]


class DjangoModuleCache:
    """Concrete :class:`ModuleCache` over the configured Django cache.

    Structurally satisfies the port (no inheritance — the seam is structural by
    design, mirroring the read-model adapters next door).

    The stored value is a plain sorted tuple rather than the ``frozenset`` itself:
    Redis serializes with pickle, and a tuple round-trips identically across Python
    versions while a set's iteration order does not. The reader wraps it back up.

    A cache that is down must not close the door on a paying organization, so every
    operation swallows backend failures and degrades to "no memo" — the entitlement
    table is the source of truth and is perfectly capable of answering on its own.
    """

    _KEY_PREFIX = "organization:modules:"

    def _key(self, organization_id: uuid.UUID) -> str:
        return f"{self._KEY_PREFIX}{organization_id}"

    def get(self, organization_id: uuid.UUID) -> frozenset[str] | None:
        try:
            stored = cache.get(self._key(organization_id))
        except Exception:  # pragma: no cover - a cache outage is not an outage
            return None
        if stored is None:
            return None
        return frozenset(stored)

    def set(self, organization_id: uuid.UUID, modules: frozenset[str], ttl_seconds: int) -> None:
        try:
            cache.set(self._key(organization_id), tuple(sorted(modules)), ttl_seconds)
        except Exception:  # pragma: no cover - a cache outage is not an outage
            return

    def invalidate(self, organization_id: uuid.UUID) -> None:
        try:
            cache.delete(self._key(organization_id))
        except Exception:  # pragma: no cover - a cache outage is not an outage
            return
