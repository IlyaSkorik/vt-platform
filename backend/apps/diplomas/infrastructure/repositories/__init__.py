"""Diplomas persistence adapters (repository implementations)."""

from __future__ import annotations

from .django_diploma_number_sequence import DjangoDiplomaNumberSequence
from .django_diploma_repository import DjangoDiplomaRepository
from .django_issued_document_repository import DjangoIssuedDocumentRepository
from .django_template_assignments import DjangoTemplateAssignments

__all__ = [
    "DjangoDiplomaNumberSequence",
    "DjangoDiplomaRepository",
    "DjangoIssuedDocumentRepository",
    "DjangoTemplateAssignments",
]
