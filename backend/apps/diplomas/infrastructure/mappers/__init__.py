"""Diplomas persistence mappers (aggregate <-> ORM row translators)."""

from __future__ import annotations

from .diploma_mapper import DiplomaMapper
from .issued_document_mapper import IssuedDocumentMapper

__all__ = ["DiplomaMapper", "IssuedDocumentMapper"]
