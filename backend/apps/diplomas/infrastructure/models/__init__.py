"""Diplomas persistence models."""

from __future__ import annotations

from .assignment import AssignmentModel
from .base import BasePersistenceModel, uuid7
from .template import TemplateModel

__all__ = ["AssignmentModel", "BasePersistenceModel", "TemplateModel", "uuid7"]
