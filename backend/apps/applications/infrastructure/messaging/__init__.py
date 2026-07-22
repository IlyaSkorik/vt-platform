"""Messaging adapters for the Applications bounded context."""

from __future__ import annotations

from .application_email_gateway import DjangoApplicantNotifier
from .event_dispatcher import NullEventPublisher

__all__ = ["DjangoApplicantNotifier", "NullEventPublisher"]
