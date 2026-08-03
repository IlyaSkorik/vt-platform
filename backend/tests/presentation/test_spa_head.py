"""Tests for the server-resolved ``<head>`` on the SPA shell.

The audience for this code is a crawler that fetches the page once and never
runs its JavaScript, so the assertions are about what is present in the *bytes*
of the response — not about what the app would eventually render.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from django.test import Client, override_settings

from config.spa import HeadFacts, head_facts_for, render_document, render_head

if TYPE_CHECKING:
    # The ORM models are imported inside the helpers so this module can be collected
    # before Django's app registry is ready; annotations still need the names.
    import uuid
    from pathlib import Path

    from apps.competitions.infrastructure.models import CompetitionModel
    from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_SHELL = """<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="description" content="Взлёт талантов — цифровая экосистема." />
    <title>Взлёт талантов</title>
  </head>
  <body><div id="root"></div></body>
</html>
"""


def _organization(name: str = "Дом талантов") -> OrganizationModel:
    from apps.organization.infrastructure.models import OrganizationModel

    return OrganizationModel.objects.create(name=name, slug="dom-talantov")


def _competition(*, organizer_id: uuid.UUID, title: str, status: str = "PUBLISHED", **extra: object) -> CompetitionModel:
    from apps.competitions.infrastructure.models import CompetitionModel

    return CompetitionModel.objects.create(
        organizer_id=organizer_id,
        status=status,
        title=title,
        season="2025/2026",
        **extra,
    )


def _shell(tmp_path: Path) -> str:
    index = tmp_path / "index.html"
    index.write_text(_SHELL, encoding="utf-8")
    return str(index)


class TestResolvingTheHead:
    def test_the_home_page_wears_the_brand_as_its_whole_title(self) -> None:
        facts = head_facts_for("/")

        assert facts.document_title.startswith("Взлёт талантов")
        assert "— Взлёт талантов —" not in facts.document_title
        assert facts.noindex is False

    def test_the_catalog_describes_itself(self) -> None:
        facts = head_facts_for("/competitions")

        assert "Фестивали" in facts.document_title
        assert facts.canonical_path == "/competitions"

    def test_a_competition_is_named_by_its_title_and_season(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        facts = head_facts_for("/competitions/vesenniy-vokal-2026")

        assert facts.document_title == "Весенний вокал — 2025/2026 — Взлёт талантов"
        assert facts.canonical_path == "/competitions/vesenniy-vokal-2026"
        assert facts.noindex is False

    def test_a_competition_resolves_by_uuid_too(self) -> None:
        org = _organization()
        competition = _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        facts = head_facts_for(f"/competitions/{competition.id}")

        # Canonicalized to the readable address: the uuid link still works, but
        # what it advertises to a crawler is the one address we want indexed.
        assert facts.canonical_path == "/competitions/vesenniy-vokal-2026"

    def test_an_unknown_competition_is_not_advertised(self) -> None:
        # The SPA answers 200 to every address, so a withdrawn or typo'd festival
        # reaches this view; naming it would preview a "not found" screen.
        facts = head_facts_for("/competitions/net-takogo")

        assert facts.noindex is True
        assert facts.canonical_path is None

    def test_a_draft_is_not_advertised_either(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, title="Черновик", status="DRAFT", slug="chernovik")

        assert head_facts_for("/competitions/chernovik").noindex is True

    def test_uses_the_organizers_own_description_when_there_is_one(self) -> None:
        org = _organization()
        _competition(
            organizer_id=org.id,
            title="Весенний вокал",
            slug="vesenniy-vokal-2026",
            description="Конкурс юных вокалистов Минской области.",
        )

        assert head_facts_for("/competitions/vesenniy-vokal-2026").description == ("Конкурс юных вокалистов Минской области.")

    def test_builds_a_description_from_the_facts_when_there_is_none(self) -> None:
        # Not a generic fallback line: a description repeated across every
        # festival is the same as none — search collapses duplicates.
        org = _organization()
        _competition(
            organizer_id=org.id,
            title="Весенний вокал",
            slug="vesenniy-vokal-2026",
            contacts_config={"venue_details": {"city": "Минск"}},
        )

        description = head_facts_for("/competitions/vesenniy-vokal-2026").description

        assert "Весенний вокал" in description
        assert "2025/2026" in description

    @pytest.mark.parametrize(
        "path",
        ["/cabinet", "/cabinet/applications", "/staff/competitions", "/platform", "/login", "/verify/abc", "/program/x", "/protocol/x"],
    )
    def test_private_and_personal_pages_refuse_indexing(self, path: str) -> None:
        facts = head_facts_for(path)

        assert facts.noindex is True
        assert facts.canonical_path is None

    def test_an_unmatched_address_is_the_404_screen(self) -> None:
        assert head_facts_for("/nothing-here").noindex is True


class TestRenderingTheHead:
    def test_marks_every_tag_so_the_client_can_take_them_over(self) -> None:
        # The load-bearing detail: the browser writer updates and removes only
        # data-seo tags. Unmarked, the client would append a second og:image
        # beside the server's, and the stale one is the one that wins.
        head = render_head(HeadFacts(title="Фестиваль", image_path="/poster.jpg", canonical_path="/competitions/x"))

        for tag in re.findall(r"<(?:meta|link)\b[^>]*>", head):
            assert "data-seo" in tag

    def test_makes_the_preview_image_absolute(self) -> None:
        head = render_head(HeadFacts(title="Ф", image_path="/home-hero-bg.png", canonical_path="/x"))

        assert re.search(r'property="og:image" content="https?://[^"]+/home-hero-bg\.png"', head)

    def test_resolves_an_uploaded_poster_against_the_host_that_serves_it(self) -> None:
        # A bundled asset and an uploaded one can live on different hosts, and an
        # og:image pointing at the wrong one previews as no image at all.
        head = render_head(
            HeadFacts(title="Ф", image_path="/media/poster.jpg", image_is_media=True, canonical_path="/x"),
            media_origin="https://api.example.by/",
        )

        assert 'content="https://api.example.by/media/poster.jpg"' in head

    def test_omits_the_image_tags_when_there_is_no_poster(self) -> None:
        head = render_head(HeadFacts(title="Ф", canonical_path="/x"))

        assert "og:image" not in head
        assert 'content="summary"' in head

    def test_withholds_the_canonical_from_a_page_it_refuses_to_index(self) -> None:
        # Pointing a crawler at a URL and telling it to stay away are
        # contradictory, and which instruction survives is the crawler's choice.
        head = render_head(HeadFacts(title="Кабинет", canonical_path="/cabinet", noindex=True))

        assert "canonical" not in head
        assert "noindex, nofollow" in head

    def test_escapes_a_title_that_could_close_the_tag(self) -> None:
        head = render_head(HeadFacts(title='Фестиваль "<script>"', canonical_path="/x"))

        assert "<script>" not in head

    def test_replaces_the_shells_title_rather_than_adding_one(self) -> None:
        document = render_document(_SHELL, HeadFacts(title="Фестивали"))

        assert document.count("<title>") == 1
        assert "<title>Фестивали — Взлёт талантов</title>" in document

    def test_replaces_the_shells_description_rather_than_adding_one(self) -> None:
        # Two descriptions and the browser reads the first — which would be the
        # generic one baked into the bundle at build time.
        document = render_document(_SHELL, HeadFacts(title="Ф", description="Про фестиваль"))

        assert document.count('name="description"') == 1
        assert "Про фестиваль" in document

    def test_leaves_the_body_to_react(self) -> None:
        document = render_document(_SHELL, HeadFacts(title="Ф"))

        assert '<div id="root"></div>' in document


class TestServingTheShell:
    def test_is_not_routed_at_all_without_a_configured_bundle(self) -> None:
        # The default today: Vite serves the SPA, and an unknown address must
        # still reach the ordinary 404 rather than a page.
        assert Client().get("/nothing-here").status_code == 404

    def test_serves_the_shell_for_a_browser_route(self, tmp_path: Path) -> None:
        with override_settings(SPA_INDEX_PATH=_shell(tmp_path)):
            response = Client().get("/competitions")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/html")
        assert b"og:title" in response.content
        assert b'<div id="root">' in response.content

    def test_names_a_competition_in_the_bytes_a_crawler_reads(self, tmp_path: Path) -> None:
        # The whole point: a preview crawler fetches once and never runs the app,
        # so the festival's name has to be in this response, not in what React
        # would eventually render.
        org = _organization()
        _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        with override_settings(SPA_INDEX_PATH=_shell(tmp_path)):
            body = Client().get("/competitions/vesenniy-vokal-2026").content.decode()

        assert "Весенний вокал" in body
        assert 'property="og:title"' in body
        assert "/competitions/vesenniy-vokal-2026" in body

    def test_never_answers_an_api_address_with_the_shell(self, tmp_path: Path) -> None:
        # A client silently parsing an HTML page as its JSON payload is a far
        # worse failure than a 404, so the catch-all must not reach /api/.
        with override_settings(SPA_INDEX_PATH=_shell(tmp_path)):
            response = Client().get("/api/v1/no-such-endpoint")

        assert response.status_code == 404
        assert b'<div id="root">' not in response.content

    def test_leaves_the_admin_alone(self, tmp_path: Path) -> None:
        with override_settings(SPA_INDEX_PATH=_shell(tmp_path)):
            response = Client().get("/admin/")

        assert b'<div id="root">' not in response.content
