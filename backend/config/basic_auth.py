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
import hmac

from django.http import HttpRequest

__all__ = ["matches", "presented_credentials"]


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
