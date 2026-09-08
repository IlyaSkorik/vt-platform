"""The OpenAPI contract and its two viewers, behind HTTP Basic auth.

``/api/schema/`` is a complete map of the API — every path, every parameter,
every field name and enum value, including the staff-only ones. Published openly
it hands over the reconnaissance an attacker would otherwise assemble request by
request, so outside development the three routes ask for a password first.

Basic auth rather than a session or a JWT because of who reads this: an
integrator, a tester, a developer on another team. They open a URL in a browser
and expect a password prompt; there is no login page to send them to and no
account to create. One shared read-only credential per deployment, kept in the
secret store (OPS-008 §9).

Three states, and the third is the point:

* **DEBUG** — served openly. Local work and the dev stack are unchanged.
* **Credentials configured** — 401 until the browser sends them.
* **Credentials unset outside DEBUG** — the routes 404, as if they did not exist.

That last one is what makes this a control rather than a suggestion. If an unset
variable meant "open", then a deployment that forgot ``API_DOCS_USER`` would
publish the entire contract and look no different from one that configured it —
the failure is invisible exactly where it matters. Failing closed turns the same
mistake into a 404 somebody reports within the hour.

404 and not 403: an address that answers 403 confirms something is there. The
schema is not a secret worth much on its own, but there is no reason to confirm
it either.

One wrinkle shapes the rest of this module. Swagger UI and ReDoc are pages that
*fetch* ``/api/schema/`` after they load — and a browser only replays Basic
credentials for the directory it was challenged on and below, so credentials
given at ``/api/schema/swagger-ui/`` do not cover the parent it then requests.
Left alone, that is a second password prompt inside the page (or, in a browser
that refuses to prompt on a subresource, a viewer stuck on "failed to load API
definition"). So a successful challenge also drops a short-lived signed cookie
scoped to ``/api/schema/``, and the fetch rides in on that.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.core import signing
from django.http import Http404, HttpRequest, HttpResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

__all__ = ["redoc_view", "schema_view", "swagger_ui_view"]

#: What the browser shows in its password prompt. Also the key it caches the
#: credentials under, so keep it stable — changing it re-prompts everyone.
_REALM = "VT Platform API docs"

#: Proof of a challenge already answered, so the viewer's own fetch of the schema
#: does not prompt again. Scoped to the docs prefix and nothing else.
_COOKIE_NAME = "api_docs_session"
_COOKIE_PATH = "/api/schema/"
#: A working session with the docs open, not a login. Expiry is enforced when the
#: signature is read, so a stale cookie is rejected server-side either way.
_COOKIE_MAX_AGE = 12 * 60 * 60

View = Callable[..., HttpResponse]


def _configured_credentials() -> tuple[str, str] | None:
    """The deployment's docs credentials, or ``None`` if either half is unset."""
    user = getattr(settings, "API_DOCS_USER", "") or ""
    password = getattr(settings, "API_DOCS_PASSWORD", "") or ""
    if not user or not password:
        return None
    return user, password


def _presented_credentials(request: HttpRequest) -> tuple[str, str] | None:
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


def _matches(presented: tuple[str, str], expected: tuple[str, str]) -> bool:
    """Compare both halves in constant time.

    ``compare_digest`` on each half, and both are always evaluated — the obvious
    ``and`` would short-circuit on a wrong username and answer measurably faster
    than a right one with a wrong password.
    """
    user_ok = hmac.compare_digest(presented[0], expected[0])
    password_ok = hmac.compare_digest(presented[1], expected[1])
    return user_ok and password_ok


def _cookie_salt(expected: tuple[str, str]) -> str:
    """Salt the cookie signature with the credentials it stands for.

    Rotating the password must log everyone out. Signing with ``SECRET_KEY``
    alone would not do that — the old cookies stay valid until they expire, so a
    credential leak could not be closed without a secret rotation. Folding a
    digest of the current pair into the salt makes every outstanding cookie
    unreadable the moment either half changes.
    """
    digest = hashlib.sha256(f"{expected[0]}:{expected[1]}".encode()).hexdigest()
    return f"api-docs:{digest}"


def _has_valid_cookie(request: HttpRequest, expected: tuple[str, str]) -> bool:
    """Whether this request carries an unexpired cookie from an earlier challenge."""
    raw = request.COOKIES.get(_COOKIE_NAME)
    if not raw:
        return False
    try:
        signing.loads(raw, salt=_cookie_salt(expected), max_age=_COOKIE_MAX_AGE)
    except signing.BadSignature:
        return False
    return True


def _issue_cookie(response: HttpResponse, expected: tuple[str, str]) -> HttpResponse:
    """Attach the proof-of-challenge cookie to a response."""
    response.set_cookie(
        _COOKIE_NAME,
        signing.dumps({"u": expected[0]}, salt=_cookie_salt(expected)),
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Strict",
    )
    return response


def _unauthorized() -> HttpResponse:
    """A 401 that makes the browser ask for a username and password."""
    response = HttpResponse("Unauthorized", status=401, content_type="text/plain; charset=utf-8")
    response["WWW-Authenticate"] = f'Basic realm="{_REALM}", charset="UTF-8"'
    return response


def basic_auth_required(view: View) -> View:
    """Gate a view behind the deployment's docs credentials."""

    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if settings.DEBUG:
            return view(request, *args, **kwargs)

        expected = _configured_credentials()
        if expected is None:
            raise Http404

        if _has_valid_cookie(request, expected):
            return view(request, *args, **kwargs)

        presented = _presented_credentials(request)
        if presented is None or not _matches(presented, expected):
            return _unauthorized()

        return _issue_cookie(view(request, *args, **kwargs), expected)

    return wrapped


schema_view = basic_auth_required(SpectacularAPIView.as_view())
swagger_ui_view = basic_auth_required(SpectacularSwaggerView.as_view(url_name="schema"))
redoc_view = basic_auth_required(SpectacularRedocView.as_view(url_name="schema"))
