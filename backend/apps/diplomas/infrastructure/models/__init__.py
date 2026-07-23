"""Diplomas persistence models."""

from __future__ import annotations

from .assignment import AssignmentModel
from .base import BasePersistenceModel, uuid7
from .template import TemplateModel
from .template_document import TemplateDocumentModel
from .template_field import TemplateFieldModel

__all__ = [
    "AssignmentModel",
    "BasePersistenceModel",
    "TemplateDocumentModel",
    "TemplateFieldModel",
    "TemplateModel",
    "uuid7",
]
