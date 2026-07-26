"""Read-side projections of the Diplomas bounded context (CQRS read side).

Pure, framework-free view DTOs and ports. Nothing here creates, numbers, renders
or mutates a diploma — the write use cases live in
:mod:`apps.diplomas.application.services` and
:mod:`apps.diplomas.application.batch_services`.
"""

from __future__ import annotations

from apps.diplomas.application.read_models.verification import (
    DiplomaVerificationReadService,
    DiplomaVerificationView,
    project_verification,
)

__all__ = [
    "DiplomaVerificationReadService",
    "DiplomaVerificationView",
    "project_verification",
]
