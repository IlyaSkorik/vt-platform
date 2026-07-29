"""Outbound messaging adapters for the Results bounded context."""

from __future__ import annotations

from .results_email_gateway import DjangoResultsNotifier

__all__ = ["DjangoResultsNotifier"]
