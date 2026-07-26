"""Composition root for the Diplomas bounded context.

The one place a framework-free use case or read model is wired to its concrete
infrastructure adapter (ARCH-001 §7.3, Dependency Inversion): the presentation
edge asks here for an assembled handler and stays ignorant of which repository or
reader sits behind the port. Adapters are stateless and cheap, so they are
assembled per call.

Not to be confused with
:mod:`apps.diplomas.presentation.api.v1.diplomas.composition`, which is about
*composing a diploma template* (its document and field layout) — a different
sense of the word entirely.
"""

from __future__ import annotations

from apps.diplomas.infrastructure.read_models import DjangoDiplomaVerificationReader

__all__ = ["build_diploma_verification_read_service"]


def build_diploma_verification_read_service() -> DjangoDiplomaVerificationReader:
    """Assemble the public diploma verification read model (QR authenticity page)."""
    return DjangoDiplomaVerificationReader()
