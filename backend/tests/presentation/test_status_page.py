"""Integration tests for the public status page.

The page's whole value is that it answers during an incident, so the tests are
mostly about the failure paths: that a broken dependency is *reported* rather
than raised, that a critical failure reaches an uptime monitor as 503 while a
degraded one deliberately does not, and that a page anyone can open never says
which line of which module went wrong.

The dependency checks themselves are stubbed wherever a verdict is asserted.
Left real, "is the whole system healthy?" is a question about the machine the
suite happens to run on — the broker in particular is absent in CI — and the
tests would report the environment instead of the code.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from django.test import Client

from config.status import Component, _check_database, _overall

if TYPE_CHECKING:
    from collections.abc import Callable


def _component(
    key: str = "database",
    *,
    health: str = "ok",
    critical: bool = True,
) -> Component:
    return Component(
        key=key,
        name=f"Компонент {key}",
        detail="Что теряет человек",
        health=health,  # type: ignore[arg-type]
        latency_ms=1.0,
        critical=critical,
    )


@pytest.fixture
def stub_checks(monkeypatch: pytest.MonkeyPatch) -> Callable[[list[Component]], None]:
    """Replace the real dependency probes with a fixed verdict."""

    def apply(components: list[Component]) -> None:
        monkeypatch.setattr("config.status._collect", lambda: components)

    return apply


class TestOverallVerdict:
    """How component states combine into the one word at the top of the page."""

    def test_everything_up_is_ok(self) -> None:
        assert _overall([_component(), _component("cache")]) == "ok"

    def test_a_degraded_component_degrades_the_whole(self) -> None:
        components = [_component(), _component("broker", health="degraded", critical=False)]

        assert _overall(components) == "degraded"

    def test_a_critical_failure_takes_the_site_down(self) -> None:
        components = [_component(health="down"), _component("cache")]

        assert _overall(components) == "down"

    def test_a_non_critical_failure_does_not(self) -> None:
        """A queue nobody is draining delays a diploma; it does not close the site.

        The distinction is the whole reason `critical` exists: it decides who gets
        woken up, so it is worth pinning rather than leaving to the caller.
        """
        components = [_component(), _component("broker", health="down", critical=False)]

        assert _overall(components) == "degraded"


class TestStatusPage:
    def test_renders_the_verdict(self, stub_checks: Callable[[list[Component]], None]) -> None:
        stub_checks([_component()])

        response = Client().get("/status")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/html")
        assert "Все системы работают" in response.content.decode()

    def test_a_critical_failure_answers_503(self, stub_checks: Callable[[list[Component]], None]) -> None:
        """The status code is the part an uptime monitor reads.

        A monitor that had to parse the page to learn the site was down would be a
        monitor nobody configures correctly.
        """
        stub_checks([_component(health="down")])

        response = Client().get("/status")

        assert response.status_code == 503
        assert "Сбой в работе" in response.content.decode()

    def test_degraded_stays_200(self, stub_checks: Callable[[list[Component]], None]) -> None:
        stub_checks([_component("broker", health="degraded", critical=False)])

        response = Client().get("/status")

        assert response.status_code == 200

    def test_is_never_cached(self, stub_checks: Callable[[list[Component]], None]) -> None:
        """A cached status page reports a moment that has passed."""
        stub_checks([_component()])

        response = Client().get("/status")

        assert "no-store" in response["Cache-Control"]

    def test_refuses_indexing(self, stub_checks: Callable[[list[Component]], None]) -> None:
        stub_checks([_component()])

        body = Client().get("/status").content.decode()

        assert 'name="robots" content="noindex,nofollow"' in body

    def test_carries_no_external_reference(self, stub_checks: Callable[[list[Component]], None]) -> None:
        """Nothing to fetch — no bundle, no font, no stylesheet, no image.

        This is the property the page exists for: it has to render over a link too
        degraded to carry the application, so a second request would defeat it.
        """
        stub_checks([_component()])

        body = Client().get("/status").content.decode()

        assert "<script" not in body
        assert "src=" not in body
        assert "<link" not in body

    def test_is_not_shadowed_by_the_spa_catch_all(self, stub_checks: Callable[[list[Component]], None]) -> None:
        """`/status` must reach this view, not the SPA shell's regex."""
        stub_checks([_component()])

        response = Client().get("/status")

        assert response.status_code == 200
        assert "Статус сервиса" in response.content.decode()


class TestStatusJson:
    def test_reports_every_component(self, stub_checks: Callable[[list[Component]], None]) -> None:
        stub_checks([_component(), _component("broker", critical=False)])

        payload = json.loads(Client().get("/status.json").content)

        assert payload["status"] == "ok"
        assert [c["key"] for c in payload["components"]] == ["database", "broker"]
        assert payload["components"][0]["critical"] is True
        assert "checkedAt" in payload

    def test_a_critical_failure_answers_503(self, stub_checks: Callable[[list[Component]], None]) -> None:
        stub_checks([_component(health="down")])

        response = Client().get("/status.json")

        assert response.status_code == 503
        assert json.loads(response.content)["status"] == "down"


class TestBrokenDependency:
    """What happens when the thing being checked is the thing that is broken."""

    @pytest.fixture
    def unreachable_database(self, monkeypatch: pytest.MonkeyPatch) -> str:
        secret = "connection refused at db-internal-7.hosting.local:5432"

        class Unreachable:
            def cursor(self) -> object:
                raise RuntimeError(secret)

        monkeypatch.setattr("config.status.connection", Unreachable())
        return secret

    def test_is_reported_rather_than_raised(self, unreachable_database: str) -> None:
        """The check reports the failure instead of propagating it.

        A health check that raises takes the status page down together with the
        dependency it was watching — exactly when somebody is reading it.
        """
        component = _check_database()

        assert component.health == "down"
        assert component.latency_ms is None

    def test_leaks_no_internals_to_a_public_page(self, unreachable_database: str) -> None:
        """The page is unauthenticated, so a failure names no host and no port.

        Deliberately runs the real ``_collect``: the leak this guards against would
        happen while assembling the page, not while rendering a stub.
        """
        response = Client().get("/status")

        assert response.status_code == 503
        body = response.content.decode()
        assert unreachable_database not in body
        assert "db-internal-7" not in body
        assert "Traceback" not in body
