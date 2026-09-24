"""Small infrastructure adapters: the clock, ids, the board slug and invite tokens.

Effects the domain deliberately does not perform itself. Injecting them is what makes
"the act was opened at 14:03" and "this invitation link" testable without waiting for
an afternoon or reading a mailbox.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Final

__all__ = ["InviteTokenFactory", "RandomSlugFactory", "SystemClock", "Uuid7Generator"]

_UUID_V7_VERSION = 7

#: No 0/O or 1/l/I: the board's link gets read off a laptop and typed into a projector
#: machine by somebody standing in a dark hall.
_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10


class SystemClock:
    """The real clock."""

    def utcnow(self) -> datetime:
        """The current UTC instant."""
        return datetime.now(UTC)


class Uuid7Generator:
    """Fresh, time-ordered UUID version 7 values (API-000 §23)."""

    def new(self) -> uuid.UUID:
        """Return a brand-new UUID version 7."""
        unix_ms = time.time_ns() // 1_000_000
        rand = int.from_bytes(os.urandom(10), "big")
        rand_a = (rand >> 68) & 0x0FFF
        rand_b = rand & ((1 << 62) - 1)
        value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
        return uuid.UUID(int=value)


class RandomSlugFactory:
    """Mints the public slug the hall's board is reached by."""

    def new_slug(self) -> str:
        return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH))


class InviteTokenFactory:
    """Mints the single-use secret an invitation link carries.

    Long and URL-safe: this is the only thing standing between a forwarded e-mail and a
    seat on a jury, so it is sized like a credential rather than like a slug.
    """

    def new_token(self) -> str:
        return secrets.token_urlsafe(32)
