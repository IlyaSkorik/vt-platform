"""Outbound messaging adapters for the Programs bounded context."""

from __future__ import annotations

from .program_email_gateway import DjangoProgramNotifier

__all__ = ["DjangoProgramNotifier"]
