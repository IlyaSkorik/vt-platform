"""Diplomas persistence models."""

from __future__ import annotations

from .assignment import AssignmentModel
from .base import BasePersistenceModel, uuid7
from .diploma import DiplomaModel, DiplomaStatusChoices
from .diploma_number_sequence import DiplomaNumberSequenceModel
from .document_type import DocumentTypeChoices
from .font_face import FontFaceModel, FontVariantChoices
from .generation_run import GenerationRunModel
from .issued_document import IssuedDocumentModel
from .print_job import PrintJobModel, PrintJobStatusChoices
from .template import TemplateModel
from .template_document import TemplateDocumentModel
from .template_field import TemplateFieldModel

__all__ = [
    "AssignmentModel",
    "BasePersistenceModel",
    "DiplomaModel",
    "DiplomaNumberSequenceModel",
    "DiplomaStatusChoices",
    "DocumentTypeChoices",
    "FontFaceModel",
    "FontVariantChoices",
    "GenerationRunModel",
    "IssuedDocumentModel",
    "PrintJobModel",
    "PrintJobStatusChoices",
    "TemplateDocumentModel",
    "TemplateFieldModel",
    "TemplateModel",
    "uuid7",
]
