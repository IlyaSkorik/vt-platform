"""Integration tests for the Basic-auth gate on the OpenAPI docs.

The gate's job is to keep a full map of the API off the open internet, so these
tests are mostly about what happens when it is *not* used correctly: no
credentials, wrong credentials, and — the case that motivates the design — a
deployment where nobody configured any. That last one must not degrade into an
open contract.

Settings are pushed per test rather than through a fixture module because the
three states are settings states: DEBUG on, credentials present, credentials
absent.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import pytest
from django.core import signing
from django.test import Client

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper

from config.api_docs import _COOKIE_NAME, _cookie_salt

USER = "docs"
PASSWORD = "s3cret-docs-password"

DOC_URLS = ["/api/schema/", "/api/schema/swagger-ui/", "/api/schema/redoc/"]


def _basic(user: str = USER, password: str = PASSWORD) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


@pytest.fixture
def configured(settings: SettingsWrapper) -> None:
    """A deployment with docs credentials set and DEBUG off."""
    settings.DEBUG = False
    settings.API_DOCS_USER = USER
    settings.API_DOCS_PASSWORD = PASSWORD


@pytest.mark.parametrize("url", DOC_URLS)
@pytest.mark.usefixtures("configured")
def test_anonymous_gets_a_password_prompt(client: Client, url: str) -> None:
    """Every doc address challenges rather than answers."""
    response = client.get(url)

    assert response.status_code == 401
    # Without the header the browser shows an error page instead of a prompt,
    # which is the difference between "ask the API owner for the password" and
    # "the docs are broken".
    assert response["WWW-Authenticate"].startswith("Basic realm=")


@pytest.mark.parametrize("url", DOC_URLS)
@pytest.mark.usefixtures("configured")
def test_correct_credentials_open_the_docs(client: Client, url: str) -> None:
    response = client.get(url, HTTP_AUTHORIZATION=_basic())

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("user", "password"),
    [
        (USER, "wrong"),
        ("wrong", PASSWORD),
        ("wrong", "wrong"),
    ],
)
@pytest.mark.usefixtures("configured")
def test_wrong_credentials_are_refused(client: Client, user: str, password: str) -> None:
    response = client.get("/api/schema/", HTTP_AUTHORIZATION=_basic(user, password))

    assert response.status_code == 401


@pytest.mark.parametrize(
    "header",
    [
        "Bearer some-token",
        "Basic",
        "Basic !!!not-base64!!!",
        # Base64 that decodes, but carries no colon to split on.
        f"Basic {base64.b64encode(b'no-separator').decode()}",
    ],
)
@pytest.mark.usefixtures("configured")
def test_malformed_authorization_is_treated_as_missing(client: Client, header: str) -> None:
    """A client that sends nonsense gets the prompt, not a 500 or a hint."""
    response = client.get("/api/schema/", HTTP_AUTHORIZATION=header)

    assert response.status_code == 401


@pytest.mark.parametrize("url", DOC_URLS)
def test_unconfigured_deployment_hides_the_docs(client: Client, settings: SettingsWrapper, url: str) -> None:
    """Credentials unset outside DEBUG means the routes are not served at all.

    This is the whole reason the gate fails closed: a forgotten variable must not
    look identical to a configured deployment while publishing the contract.
    """
    settings.DEBUG = False
    settings.API_DOCS_USER = ""
    settings.API_DOCS_PASSWORD = ""

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.parametrize("url", DOC_URLS)
def test_half_configured_deployment_hides_the_docs(client: Client, settings: SettingsWrapper, url: str) -> None:
    """A username with no password is not a credential — same failure, same 404."""
    settings.DEBUG = False
    settings.API_DOCS_USER = USER
    settings.API_DOCS_PASSWORD = ""

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.parametrize("url", DOC_URLS)
def test_debug_keeps_the_docs_open(client: Client, settings: SettingsWrapper, url: str) -> None:
    """Local work is untouched: no credentials, no prompt."""
    settings.DEBUG = True
    settings.API_DOCS_USER = ""
    settings.API_DOCS_PASSWORD = ""

    response = client.get(url)

    assert response.status_code == 200


@pytest.mark.usefixtures("configured")
def test_a_challenge_answered_once_covers_the_schema_fetch(client: Client) -> None:
    """Opening Swagger UI must not prompt a second time when the page fetches.

    Basic credentials are replayed only for the directory they were given on and
    below, so ``/api/schema/swagger-ui/`` does not cover the ``/api/schema/`` the
    page then requests. The cookie issued on the challenge is what closes that
    gap — without it the viewer stalls on "failed to load API definition".
    """
    page = client.get("/api/schema/swagger-ui/", HTTP_AUTHORIZATION=_basic())
    assert page.status_code == 200
    assert _COOKIE_NAME in page.cookies

    # The client keeps the cookie; the fetch carries no Authorization header.
    fetched = client.get("/api/schema/")

    assert fetched.status_code == 200


@pytest.mark.usefixtures("configured")
def test_the_cookie_is_scoped_to_the_docs_and_hidden_from_scripts(client: Client) -> None:
    cookie = client.get("/api/schema/", HTTP_AUTHORIZATION=_basic()).cookies[_COOKIE_NAME]

    assert cookie["path"] == "/api/schema/"
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    # DEBUG is off in this fixture, so the cookie must never travel in clear text.
    assert cookie["secure"]


@pytest.mark.usefixtures("configured")
def test_rotating_the_password_invalidates_outstanding_cookies(client: Client, settings: SettingsWrapper) -> None:
    """The point of rotating a leaked password is that it takes effect now."""
    client.get("/api/schema/", HTTP_AUTHORIZATION=_basic())
    assert client.get("/api/schema/").status_code == 200

    settings.API_DOCS_PASSWORD = "rotated-after-a-leak"

    assert client.get("/api/schema/").status_code == 401


@pytest.mark.usefixtures("configured")
def test_a_forged_cookie_is_not_a_credential(client: Client) -> None:
    """Unsigned or foreign-signed values must not pass for a challenge."""
    client.cookies[_COOKIE_NAME] = signing.dumps({"u": USER}, salt="some-other-salt")

    assert client.get("/api/schema/").status_code == 401


@pytest.mark.usefixtures("configured")
def test_an_expired_cookie_is_not_a_credential(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Age is enforced server-side, not just by the browser's own expiry."""
    salt = _cookie_salt((USER, PASSWORD))
    client.cookies[_COOKIE_NAME] = signing.dumps({"u": USER}, salt=salt)
    monkeypatch.setattr("config.api_docs._COOKIE_MAX_AGE", -1)

    assert client.get("/api/schema/").status_code == 401
