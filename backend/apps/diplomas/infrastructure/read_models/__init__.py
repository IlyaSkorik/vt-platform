"""Concrete read-model adapters for the Diplomas bounded context.

Read side only (CQRS): these query the ``diplomas_*`` tables directly and project
rows into the flat views published by
:mod:`apps.diplomas.application.read_models`. They rehydrate no aggregate and
enforce no invariant (ARCH-001 §7.2, §14).
"""

from __future__ import annotations

from apps.diplomas.infrastructure.read_models.participant_documents import (
    DjangoParticipantDocumentsReader,
)
from apps.diplomas.infrastructure.read_models.verification import DjangoDiplomaVerificationReader

__all__ = ["DjangoDiplomaVerificationReader", "DjangoParticipantDocumentsReader"]
