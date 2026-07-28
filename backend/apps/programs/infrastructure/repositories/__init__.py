"""Persistence adapters for the Programs bounded context."""

from __future__ import annotations

from .django_program_repository import DjangoProgramRepository

__all__ = ["DjangoProgramRepository"]
