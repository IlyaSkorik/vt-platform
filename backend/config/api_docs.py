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

from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from config.basic_auth import ChallengeCookie
from config.basic_auth import matches as _matches
from config.basic_auth import presented_credentials as _presented_credentials
from config.basic_auth import unauthorized as _unauthorized

__all__ = ["redoc_view", "schema_view", "swagger_ui_view"]

#: What the browser shows in its password prompt. Also the key it caches the
#: credentials under, so keep it stable — changing it re-prompts everyone.
_REALM = "VT Platform API docs"

#: Proof of a challenge already answered, so the viewer's own fetch of the schema
#: does not prompt again. Scoped to the docs prefix and nothing else, and Strict
#: because these addresses are opened deliberately rather than arrived at from a
#: link somebody was sent.
_COOKIE = ChallengeCookie(
    name="api_docs_session",
    path="/api/schema/",
    # A working session with the docs open, not a login. Expiry is enforced when the
    # signature is read, so a stale cookie is rejected server-side either way.
    max_age=12 * 60 * 60,
    salt_prefix="api-docs",
)

View = Callable[..., HttpResponse]


def _configured_credentials() -> tuple[str, str] | None:
    """The deployment's docs credentials, or ``None`` if either half is unset."""
    user = getattr(settings, "API_DOCS_USER", "") or ""
    password = getattr(settings, "API_DOCS_PASSWORD", "") or ""
    if not user or not password:
        return None
    return user, password


def basic_auth_required(view: View) -> View:
    """Gate a view behind the deployment's docs credentials."""

    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if settings.DEBUG:
            return view(request, *args, **kwargs)

        expected = _configured_credentials()
        if expected is None:
            raise Http404

        if _COOKIE.is_valid(request, expected):
            return view(request, *args, **kwargs)

        presented = _presented_credentials(request)
        if presented is None or not _matches(presented, expected):
            return _unauthorized(_REALM)

        return _COOKIE.attach(view(request, *args, **kwargs), expected)

    return wrapped


schema_view = basic_auth_required(SpectacularAPIView.as_view())
swagger_ui_view = basic_auth_required(SpectacularSwaggerView.as_view(url_name="schema"))
redoc_view = basic_auth_required(SpectacularRedocView.as_view(url_name="schema"))
