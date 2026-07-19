"""Messaging adapters for the Identity & Access bounded context.

Concrete infrastructure implementations of the outbound messaging/event ports
declared in :mod:`apps.identity.application.interfaces`:

* :class:`DjangoEmailGateway`            — the ``EmailGateway`` port over Django core mail.
* :class:`SignedVerificationTokenService`— the ``VerificationTokenService`` port over
  Django signing (email verification).
* :class:`SignedPasswordResetTokenService`— the same port for the password-reset flow
  (distinct salt/route).
* :class:`EventDispatcher`               — the ``EventPublisher`` port, dispatching
  domain events to in-process subscribers synchronously.

These depend inward on the application ports and the domain; nothing in the
application or domain layers depends on this package (ARCH-001 §7.2).
"""

from __future__ import annotations

from apps.identity.infrastructure.messaging.email_gateway import DjangoEmailGateway
from apps.identity.infrastructure.messaging.event_dispatcher import EventDispatcher
from apps.identity.infrastructure.messaging.password_reset_token_service import (
    SignedPasswordResetTokenService,
)
from apps.identity.infrastructure.messaging.verification_token_service import (
    SignedVerificationTokenService,
)

__all__ = [
    "DjangoEmailGateway",
    "EventDispatcher",
    "SignedPasswordResetTokenService",
    "SignedVerificationTokenService",
]
