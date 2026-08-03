"""Concrete read-model adapters for the Competitions bounded context.

Read side only (CQRS): these query the ``competitions_*`` tables directly and
project rows into the flat views published by
:mod:`apps.competitions.application.read_models`. They rehydrate no aggregate and
enforce no invariant (ARCH-001 §7.2, §14).
"""

from __future__ import annotations

from apps.competitions.infrastructure.read_models.public_catalog import (
    DjangoPublicCatalogReader,
)
from apps.competitions.infrastructure.read_models.registration import (
    DjangoRegistrationReader,
)

__all__ = ["DjangoPublicCatalogReader", "DjangoRegistrationReader"]
