"""Anti-corruption layer: this context's window onto the rest of the platform."""

from __future__ import annotations

from .nominee_catalog import DjangoNomineeCatalog

__all__ = ["DjangoNomineeCatalog"]
