"""``Sha256InvitationTokenHasher`` — the concrete :class:`TokenHasher` adapter.

Mints a high-entropy raw invitation secret and computes its SHA-256 digest; the
raw secret goes into the emailed link and is **never** persisted, only the digest
is (the same philosophy as password storage). Acceptance recomputes the digest of
a presented raw token via :meth:`hash` for a hash-vs-hash lookup.

SHA-256 (not Argon2) is appropriate here because the token is a 256-bit random
secret, not a low-entropy human password: there is nothing to brute-force, so a
fast digest that yields a stable, indexable lookup key is exactly right.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Final

from apps.organization.application.interfaces import IssuedInvitationToken
from apps.organization.domain.value_objects import InvitationTokenHash

__all__ = ["Sha256InvitationTokenHasher"]

#: Bytes of entropy in a raw invitation secret (256 bits → 43-char urlsafe token).
_TOKEN_BYTES: Final = 32


class Sha256InvitationTokenHasher:
    """Generate and hash invitation secrets (``TokenHasher`` port).

    Structurally satisfies the port (no ``Protocol`` inheritance — the seam is
    structural by design).
    """

    def generate(self) -> IssuedInvitationToken:
        """Mint a fresh URL-safe raw secret and its :class:`InvitationTokenHash`."""
        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        return IssuedInvitationToken(raw_token=raw_token, token_hash=self.hash(raw_token))

    def hash(self, raw_token: str) -> InvitationTokenHash:
        """Compute the SHA-256 hex digest of ``raw_token``."""
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        return InvitationTokenHash(digest)
