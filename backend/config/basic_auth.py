"""Reading and checking an ``Authorization: Basic`` header.

Two things in this project ask for a password at the edge: the OpenAPI contract
and its viewers (:mod:`config.api_docs`), and — on a deployment that is not meant
to be public at all — every address on it
(:class:`config.middleware.SiteGateMiddleware`).

They differ in what they do with the answer and in what an unset credential
means, but the two operations underneath are the same. Both are security
relevant enough that one implementation to read and to test is worth more than
the indirection costs.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
from dataclasses import dataclass
from typing import Literal

from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse

__all__ = ["ChallengeCookie", "matches", "presented_credentials", "unauthorized"]


def presented_credentials(request: HttpRequest) -> tuple[str, str] | None:
    """Parse ``Authorization: Basic``, or ``None`` if absent or malformed.

    Malformed is treated as absent on purpose: a client that sent something
    unreadable gets the same 401 prompt as one that sent nothing, rather than an
    error that says which part it got wrong.
    """
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, payload = header.partition(" ")
    if scheme.lower() != "basic" or not payload:
        return None
    try:
        decoded = base64.b64decode(payload.strip(), validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    user, separator, password = decoded.partition(":")
    if not separator:
        return None
    return user, password


def matches(presented: tuple[str, str], expected: tuple[str, str]) -> bool:
    """Compare both halves in constant time.

    ``compare_digest`` on each half, and both are always evaluated — the obvious
    ``and`` would short-circuit on a wrong username and answer measurably faster
    than a right one with a wrong password.
    """
    user_ok = hmac.compare_digest(presented[0], expected[0])
    password_ok = hmac.compare_digest(presented[1], expected[1])
    return user_ok and password_ok


@dataclass(frozen=True)
class ChallengeCookie:
    """Proof that a Basic challenge was already answered.

    A browser replays Basic credentials by itself, so at first glance this is
    redundant. It is not, and for two different reasons in the two places it is
    used:

    * The docs viewers *fetch* the schema after they load, and a browser only
      replays credentials for the directory it was challenged on and below — so a
      password given at ``/api/schema/swagger-ui/`` does not cover the parent it
      then requests, and the page prompts again inside itself.

    * The site gate sits in front of an API that uses ``401`` for its own
      purposes: the SPA asks to refresh a session on every cold load and is
      correctly refused when there is none. A browser that gets a 401 where it
      just sent credentials concludes they were rejected, drops them, and prompts
      again — on every single page load.

    In both cases the fix is the same: once the challenge is answered, authorize
    by cookie and stop depending on what the browser decides to replay.

    Signed, not encrypted — it carries no secret, only the fact of a successful
    challenge. The signature is salted with a digest of the credentials it stands
    for, so rotating the password invalidates every outstanding cookie at once;
    signing with ``SECRET_KEY`` alone would leave them valid until they expired,
    and a leak could not be closed without rotating the secret.
    """

    name: str
    path: str
    max_age: int
    #: Namespaces the signature, so a cookie minted for one gate cannot be
    #: presented to the other.
    salt_prefix: str
    #: ``Lax`` where the address is arrived at from a link somebody was sent —
    #: ``Strict`` would withhold the cookie on that first navigation and put the
    #: prompt back exactly where it was removed.
    samesite: Literal["Lax", "Strict"] = "Strict"

    def salt(self, expected: tuple[str, str]) -> str:
        """The signing salt, bound to the credentials this cookie stands for."""
        digest = hashlib.sha256(f"{expected[0]}:{expected[1]}".encode()).hexdigest()
        return f"{self.salt_prefix}:{digest}"

    def is_valid(self, request: HttpRequest, expected: tuple[str, str]) -> bool:
        """Whether this request carries an unexpired cookie from an earlier challenge."""
        raw = request.COOKIES.get(self.name)
        if not raw:
            return False
        try:
            signing.loads(raw, salt=self.salt(expected), max_age=self.max_age)
        except signing.BadSignature:
            return False
        return True

    def attach(self, response: HttpResponse, expected: tuple[str, str]) -> HttpResponse:
        """Put the proof-of-challenge cookie on a response."""
        response.set_cookie(
            self.name,
            signing.dumps({"u": expected[0]}, salt=self.salt(expected)),
            max_age=self.max_age,
            path=self.path,
            httponly=True,
            secure=not settings.DEBUG,
            samesite=self.samesite,
        )
        return response


def unauthorized(realm: str) -> HttpResponse:
    """A 401 that makes the browser ask for a username and password."""
    response = HttpResponse("Unauthorized", status=401, content_type="text/plain; charset=utf-8")
    response["WWW-Authenticate"] = f'Basic realm="{realm}", charset="UTF-8"'
    return response
