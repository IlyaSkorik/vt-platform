"""Side-effect handlers that react to Identity domain events (ARCH-001 §4.8).

Where a command handler *orchestrates* a use case and **returns** the events the
domain produced, the handlers here **consume** those events to perform follow-on
side effects — the outbound half of the pipeline. They are still application
layer: framework-free orchestrators that depend only on ports
(:mod:`apps.identity.application.interfaces`), never on Django, SMTP, or a signer.

Implemented here:

* :class:`SendVerificationEmailOnUserRegistered` — on ``UserRegistered``, mint a
  verification link and send the verification email (IDN-002).
"""

from __future__ import annotations

from apps.identity.application.interfaces import (
    Clock,
    EmailGateway,
    VerificationTokenService,
)
from apps.identity.domain.events import UserRegistered

__all__ = ["SendVerificationEmailOnUserRegistered"]


class SendVerificationEmailOnUserRegistered:
    """React to ``UserRegistered`` by emailing an email-verification link (IDN-002).

    The consumer that closes the registration → verification loop: it stamps the
    link with the current instant (so the domain's
    :class:`~apps.identity.domain.policies.EmailVerificationPolicy` owns expiry),
    asks the :class:`VerificationTokenService` for a signed, user-clickable link,
    and hands it to the :class:`EmailGateway`. It holds no business rule of its own
    and performs no persistence; it only turns a recorded fact into an outbound
    message through injected ports.
    """

    def __init__(
        self,
        *,
        email_gateway: EmailGateway,
        tokens: VerificationTokenService,
        clock: Clock,
    ) -> None:
        self._email_gateway = email_gateway
        self._tokens = tokens
        self._clock = clock

    def handle(self, event: UserRegistered) -> None:
        """Send the verification email for a freshly registered account."""
        issued_at = self._clock.utcnow()
        link = self._tokens.issue_link(user_id=event.aggregate_id, issued_at=issued_at)
        self._email_gateway.send_verification_email(
            email=event.email,
            full_name=event.full_name,
            verification_url=link,
            locale=event.locale,
        )
