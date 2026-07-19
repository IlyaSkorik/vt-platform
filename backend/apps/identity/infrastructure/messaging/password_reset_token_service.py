"""``SignedPasswordResetTokenService`` — the signed-link adapter for password reset.

Concrete implementation of the
:class:`~apps.identity.application.interfaces.VerificationTokenService` port over
Django's cryptographic signing (:mod:`django.core.signing`), for the
password-recovery flow (IDN-004). It mints the opaque, tamper-evident token
embedded in the reset link and later verifies a token a user returns, without the
application or domain layers knowing anything about the signing key, the token
codec, or the web client's URL shape (ARCH-001 §7.2, §7.3).

It mirrors
:class:`~apps.identity.infrastructure.messaging.verification_token_service.SignedVerificationTokenService`
but is a **distinct** adapter on purpose:

* **A separate salt.** Reset tokens are namespaced under ``identity.password-reset``,
  so an email-verification token can never be replayed as a reset token (nor vice
  versa) even though both are minted under the same ``SECRET_KEY``. This isolation
  is a security requirement, not a stylistic choice — a reset token grants
  credential control.
* **A separate web route.** The link targets the client's ``/reset-password`` page,
  which collects the new password (whereas verification targets ``/verify-email``).
* **Expiry belongs to the domain.** The token carries the instant it was issued
  (``issued_at``); this adapter enforces no ``max_age``. Whether the link is still
  valid is owned by
  :class:`~apps.identity.domain.policies.PasswordResetPolicy`, so an expired link
  is a distinct, domain-decided ``410`` rather than an opaque signer error.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing

from apps.identity.application.exceptions import InvalidVerificationTokenError
from apps.identity.application.interfaces import VerificationToken
from apps.identity.domain.value_objects import UserId

__all__ = ["SignedPasswordResetTokenService"]

#: Namespacing salt so a reset token can never be replayed as another kind of
#: signed value (notably an email-verification token) minted under the same
#: ``SECRET_KEY``.
_SALT: Final = "identity.password-reset"

#: Web-client route that reads the ``token`` query parameter and collects the new
#: password.
_RESET_PATH: Final = "/reset-password"


class SignedPasswordResetTokenService:
    """Sign and verify password-reset links (``VerificationTokenService`` port).

    ``base_url`` is the web client's origin (no trailing slash) used to build the
    user-facing link; it defaults to ``settings.FRONTEND_BASE_URL``. Structurally
    satisfies the port (it does not inherit the ``Protocol`` — the seam is
    structural by design, keeping the application core free of an outward edge).
    """

    def __init__(self, *, base_url: str | None = None) -> None:
        raw = base_url if base_url is not None else settings.FRONTEND_BASE_URL
        self._base_url = raw.rstrip("/")

    def issue_link(self, *, user_id: UserId, issued_at: datetime) -> str:
        """Mint a signed token for ``user_id`` stamped ``issued_at`` and return its link."""
        payload = {"user_id": user_id.json(), "issued_at": issued_at.isoformat()}
        token = signing.dumps(payload, salt=_SALT)
        query = urlencode({"token": token})
        return f"{self._base_url}{_RESET_PATH}?{query}"

    def verify(self, token: str) -> VerificationToken:
        """Verify ``token``'s signature and return its payload.

        Raises :class:`InvalidVerificationTokenError` if the token is malformed,
        tampered with, or its signature does not verify. Expiry is **not** checked
        here (see the module docstring): a well-formed token's ``issued_at`` is
        returned so the domain policy decides validity.
        """
        try:
            payload = signing.loads(token, salt=_SALT)
        except signing.BadSignature as exc:
            raise InvalidVerificationTokenError("The password reset token is invalid.") from exc
        if not isinstance(payload, dict):
            raise InvalidVerificationTokenError("The password reset token is malformed.")
        raw_user_id = payload.get("user_id")
        raw_issued_at = payload.get("issued_at")
        if not isinstance(raw_user_id, str) or not isinstance(raw_issued_at, str):
            raise InvalidVerificationTokenError("The password reset token is malformed.")
        try:
            user_id = UserId.from_string(raw_user_id)
            issued_at = datetime.fromisoformat(raw_issued_at)
        except ValueError as exc:
            raise InvalidVerificationTokenError("The password reset token is malformed.") from exc
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=UTC)
        return VerificationToken(user_id=user_id, issued_at=issued_at)
