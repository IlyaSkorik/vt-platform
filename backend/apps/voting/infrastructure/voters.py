"""Recognizing a voter, gently.

This is the whole of the "soft" anti-fraud tier, and it is worth being honest
about what it is: it stops somebody holding F5, somebody sharing a link in a chat
and pressing it twice, and a script running from one machine. It does not stop a
determined person with a VPN and a private window, and the organizer's interface
says so in as many words rather than letting them promise the hall otherwise.

**How a voter is recognized.** On the first read of a voting page the server mints
a random token and asks the browser to keep it in an httpOnly cookie. The token
itself is never stored; what goes in the database is

    voter_key = sha256(pepper ‖ ballot_id ‖ token)

Hashed, so a dump of the votes table does not let anybody vote as somebody else.
Salted with a server-side pepper, so the hash cannot be recomputed from a stolen
token alone. Mixed with the ballot id, so the same visitor voting in two ballots
produces two unrelated keys and this table can never be used to follow a person
around the platform.

**Where from** is the same construction over a coarse address prefix — a /24 for
IPv4, a /64 for IPv6 — and never the address itself. Enough to notice that four
thousand votes arrived from one place; useless for locating anybody (LEGAL-001).

The whole thing hangs behind :class:`~apps.voting.application.interfaces.VoterIdentity`,
so recognizing voters more strictly later — a confirmed e-mail, a Telegram login,
an SMS code — replaces this file and changes nothing above it.
"""

from __future__ import annotations

import hashlib
import ipaddress
import secrets
import uuid
from typing import Any, Final

from django.conf import settings

from apps.voting.application.interfaces import VoterTokens
from apps.voting.domain.vote import NetworkKey, VoterKey

__all__ = [
    "COOKIE_NAME",
    "COOKIE_PATH",
    "CookieVoterIdentity",
    "cookie_max_age",
]

#: The cookie the voter token rides in. httpOnly and path-scoped: it is not for
#: JavaScript and has no business being sent to any other endpoint.
COOKIE_NAME: Final = "vt_voter"
COOKIE_PATH: Final = "/api/v1/public/ballots"

#: How long the browser keeps it. Long enough to outlive any ballot's repeat
#: window, short enough that it is not a permanent mark on somebody's browser.
_COOKIE_MAX_AGE_SECONDS: Final = 60 * 60 * 24 * 30

_TOKEN_BYTES: Final = 32
_IPV4_PREFIX: Final = 24
_IPV6_PREFIX: Final = 64


def cookie_max_age() -> int:
    """How long the voter cookie should live, in seconds."""
    return _COOKIE_MAX_AGE_SECONDS


def _pepper() -> bytes:
    """The server-side secret mixed into every key.

    Derived from ``SECRET_KEY`` rather than configured separately: it needs exactly
    the same handling and rotating it independently would only mean one more secret
    nobody rotates. Rotating it invalidates every voter's recognition, which is the
    correct consequence — the keys become unlinkable, which is the point of them.
    """
    return hashlib.sha256(f"voting:{settings.SECRET_KEY}".encode()).digest()


def _derive(*parts: str) -> str:
    digest = hashlib.sha256(_pepper())
    for part in parts:
        digest.update(b"\x1f")
        digest.update(part.encode("utf-8"))
    return digest.hexdigest()


def _client_address(request: Any) -> str:
    """The address the request appears to come from.

    ``X-Forwarded-For``'s **first** entry is the client as the edge proxy saw it;
    the rest are proxies. A client can forge the header, but behind our own proxy
    the header is rewritten, and a forged value only ever moves somebody into a
    different bucket of a soft brake — it does not let them past a hard gate,
    because there is no hard gate here.
    """
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or (request.META.get("REMOTE_ADDR") or "")


def _network_prefix(address: str) -> str:
    """A coarse prefix of the address, or a marker when there is nothing to read."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return "unknown"
    prefix = _IPV4_PREFIX if parsed.version == 4 else _IPV6_PREFIX
    network = ipaddress.ip_network(f"{parsed}/{prefix}", strict=False)
    return str(network)


class CookieVoterIdentity:
    """Concrete :class:`VoterIdentity` over an httpOnly cookie and a coarse prefix.

    Structurally satisfies the port (no inheritance — the seam is structural by
    design, as elsewhere in this codebase).
    """

    def recognize(self, request: object, *, ballot_id: uuid.UUID) -> VoterTokens:
        """Identify the caller, minting a token for a first-time visitor."""
        presented = self._presented_token(request)
        token = presented or secrets.token_urlsafe(_TOKEN_BYTES)
        address = _client_address(request)
        return VoterTokens(
            voter=VoterKey(_derive("voter", str(ballot_id), token)),
            network=NetworkKey(_derive("network", str(ballot_id), _network_prefix(address))),
            issued=presented is None,
            raw_token=None if presented else token,
        )

    @staticmethod
    def _presented_token(request: object) -> str | None:
        cookies = getattr(request, "COOKIES", None) or {}
        raw = cookies.get(COOKIE_NAME)
        if not isinstance(raw, str):
            return None
        token = raw.strip()
        # A token of an implausible length was not minted here; treat it as absent
        # rather than as a key, so a hand-written cookie cannot pin somebody's slot.
        return token if 16 <= len(token) <= 128 else None
