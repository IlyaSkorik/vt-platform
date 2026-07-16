"""File-storage adapters for the Applications bounded context."""

from __future__ import annotations

from .django_file_storage import DjangoFileStorage

__all__ = ["DjangoFileStorage"]
