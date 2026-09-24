"""Outbound messaging adapters for the Judging bounded context."""

from .jury_email_gateway import DjangoJuryNotifier

__all__ = ["DjangoJuryNotifier"]
