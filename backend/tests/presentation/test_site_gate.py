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
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from django.core import signing
from django.test import Client

from config.middleware import _GATE_COOKIE

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


class TestTheChallengeIsAnsweredOnce:
    """Why the cookie exists at all.

    Without it the stand re-prompts on nearly every page load, and not because
    anything is broken: the SPA asks to refresh a session on every cold start, is
    correctly refused with a 401 when there is none, and the browser reads that as
    its Basic credentials having been rejected — drops them and asks again.
    """

    def test_a_successful_challenge_hands_out_a_cookie(self, gated: Client) -> None:
        response = gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic())

        cookie = response.cookies[_GATE_COOKIE.name]
        assert cookie.value
        # The whole site, not one prefix: the gate stands in front of every address.
        assert cookie["path"] == "/"
        # Reached by clicking a link somebody was sent, so Strict would withhold it on
        # exactly that first navigation and put the prompt straight back.
        assert cookie["samesite"] == "Lax"
        assert cookie["httponly"]

    def test_the_cookie_alone_is_enough(self, gated: Client) -> None:
        """No Authorization header at all — which is the state a browser lands in."""
        gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic())

        response = gated.get(OPEN_URL)

        assert response.status_code == 200
        # No challenge, so nothing tells the browser to prompt again.
        assert "WWW-Authenticate" not in response

    def test_an_api_401_does_not_re_challenge(self, gated: Client) -> None:
        """The 401 the SPA provokes must not carry a Basic challenge of ours."""
        gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic())

        response = gated.get("/api/v1/me/documents")

        assert response.status_code != 200, "expected the API's own refusal, not the gate's"
        assert "Basic" not in response.get("WWW-Authenticate", "")

    def test_the_cookie_survives_a_new_browser_session(self, gated: Client, settings: SettingsWrapper) -> None:
        """The control for the rotation test below: the cookie is what does the work."""
        gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic())
        issued = gated.cookies[_GATE_COOKIE.name].value

        # A client of its own, so nothing but the cookie is carried over. The middleware
        # reads the credentials once when its chain is built, which is why the password
        # has to be in place before this one is constructed.
        settings.SITE_GATE_PASSWORD = PASSWORD
        fresh = Client()
        fresh.cookies[_GATE_COOKIE.name] = issued

        assert fresh.get(OPEN_URL).status_code == 200

    def test_rotating_the_password_invalidates_it(self, gated: Client, settings: SettingsWrapper) -> None:
        """A leaked cookie is closed by changing the password, without touching SECRET_KEY."""
        gated.get(OPEN_URL, HTTP_AUTHORIZATION=_basic())
        issued = gated.cookies[_GATE_COOKIE.name].value

        settings.SITE_GATE_PASSWORD = "rotated-after-a-leak"
        rotated = Client()
        rotated.cookies[_GATE_COOKIE.name] = issued

        # The signature is salted with the credentials, so the same cookie that the
        # control above accepts is unreadable the moment either half changes.
        assert rotated.get(OPEN_URL).status_code == 401

    def test_a_forged_cookie_is_refused(self, gated: Client) -> None:
        """Signed, so a value somebody made up does not open anything."""
        gated.cookies[_GATE_COOKIE.name] = "not-a-signed-value"

        assert gated.get(OPEN_URL).status_code == 401

    def test_an_expired_cookie_is_refused(self, gated: Client, monkeypatch: pytest.MonkeyPatch) -> None:
        """Age is enforced server-side, not left to the browser's own expiry."""
        salt = _GATE_COOKIE.salt((USER, PASSWORD))
        gated.cookies[_GATE_COOKIE.name] = signing.dumps({"u": USER}, salt=salt)
        monkeypatch.setattr("config.middleware._GATE_COOKIE", replace(_GATE_COOKIE, max_age=-1))

        assert gated.get(OPEN_URL).status_code == 401
