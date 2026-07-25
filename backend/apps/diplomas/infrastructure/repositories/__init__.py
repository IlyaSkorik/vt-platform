"""Diplomas persistence adapters (repository implementations)."""

from __future__ import annotations

from .django_diploma_number_sequence import DjangoDiplomaNumberSequence
from .django_diploma_repository import DjangoDiplomaRepository

__all__ = ["DjangoDiplomaNumberSequence", "DjangoDiplomaRepository"]
