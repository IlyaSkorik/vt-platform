"""Concrete repository adapters for the Results bounded context."""

from __future__ import annotations

from .django_protocol_repository import DjangoProtocolRepository

__all__ = ["DjangoProtocolRepository"]
