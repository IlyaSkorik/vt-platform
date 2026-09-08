"""Integration tests for the whole-site Basic-auth gate.

The gate exists for the staging stand: a complete copy of the site, on a
guessable subdomain, that no crawler and no passer-by should reach. Production
runs with it unset, so the tests that matter most are the two ends — that unset
really does serve the site openly, and that configured really does close
*everything* except the two probes a deploy depends on.

The middleware chain is built once per handler, and the gate decides at that
moment whether it exists at all. Each test therefore constructs its own
``Client`` after pushing settings, rather than using the shared fixture.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import pytest
from django.test import Client

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper

USER = "stand"
PASSWORD = "s3cret-stand-password"

#: A cheap public address that needs no database and no session.
OPEN_URL = "/robots.txt"


def _basic(user: str = USER, password: str = PASSWORD) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


@pytest.fixture
def gated(settings: SettingsWrapper) -> Client:
    """A deployment with the gate configured, and a client that sees it."""
    settings.SITE_GATE_USER = USER
    settings.SITE_GATE_PASSWORD = PASSWORD
    return Client()


@pytest.fixture
def ungated(settings: SettingsWrapper) -> Client:
    """A deployment with the gate unset — production's shape."""
    settings.SITE_GATE_USER = ""
    settings.SITE_GATE_PASSWORD = ""
    return Client()


class TestUnconfigured:
    """Unset must mean open: production is the public site."""

    def test_the_site_is_served_without_a_password(self, ungated: Client) -> None:
        assert ungated.get(OPEN_URL).status_code == 200

    def test_no_challenge_is_offered(self, ungated: Client) -> None:
        """No `WWW-Authenticate`, so no browser anywhere shows a prompt."""
        assert "WWW-Authenticate" not in ungated.get(OPEN_URL)


class TestConfigured:
    def test_anonymous_is_challenged(self, gated: Client) -> None:
        response = gated.get(OPEN_URL)

        assert response.status_code == 401
        # Without this header a browser shows the body instead of asking, and
        # whoever was handed the address has no way in.
        assert response["WWW-Authenticate"].startswith("Basic realm=")

    def test_the_right_credentials_are_let_through(self, gated: Client) -> None:
        assert gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic()).status_code == 200

    @pytest.mark.parametrize(
        ("user", "password"),
        [
            (USER, "wrong"),
            ("wrong", PASSWORD),
            ("wrong", "wrong"),
        ],
    )
    def test_wrong_credentials_are_refused(self, gated: Client, user: str, password: str) -> None:
        response = gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic(user, password))

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "header",
        [
            "",
            "Basic",
            "Basic !!!not-base64!!!",
            "Bearer some.jwt.token",
            f"Basic {base64.b64encode(b'no-colon-here').decode()}",
        ],
    )
    def test_a_malformed_header_is_treated_as_none(self, gated: Client, header: str) -> None:
        """The same 401 as sending nothing, rather than a hint about which part was wrong."""
        response = gated.get(OPEN_URL, HTTP_AUTHORIZATION=header)

        assert response.status_code == 401

    def test_the_admin_is_behind_it_too(self, gated: Client) -> None:
        """Not just the SPA: the stand's admin is a way into the stand's data."""
        assert gated.get("/admin/login/").status_code == 401

    def test_the_api_is_behind_it_too(self, gated: Client) -> None:
        assert gated.get("/api/v1/public/festivals").status_code == 401


class TestProbesStayOpen:
    """The gate must not close what the rollout itself depends on."""

    @pytest.mark.parametrize("url", ["/healthz", "/readyz"])
    def test_the_probes_answer_without_credentials(self, gated: Client, url: str) -> None:
        response = gated.get(url)

        assert response.status_code == 200
        # Both are fixed literals — there is nothing behind them to protect, which
        # is what makes exempting them safe rather than merely convenient.
        assert response.json()["status"] in {"ok", "ready"}

    def test_nothing_else_is_exempt_by_accident(self, gated: Client) -> None:
        """`/status` reports the deployment's health to a person; on a stand it stays shut."""
        assert gated.get("/status").status_code == 401
