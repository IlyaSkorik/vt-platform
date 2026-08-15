"""Integration tests for ``robots.txt``, ``sitemap.xml`` and ``llms.txt``.

These are the documents a machine reads before it reads the site, and all three
are generated rather than shipped as files — so they are worth testing exactly
like an endpoint: what they list, and more importantly what they refuse to list.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from xml.etree import ElementTree

import pytest
from django.test import Client

from config.seo import site_url

if TYPE_CHECKING:
    # The ORM models are imported inside the helpers so this module can be collected
    # before Django's app registry is ready; annotations still need the names.
    from apps.competitions.infrastructure.models import CompetitionModel
    from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _organization(name: str = "Дом талантов") -> OrganizationModel:
    from apps.organization.infrastructure.models import OrganizationModel

    return OrganizationModel.objects.create(name=name, slug="dom-talantov")


def _competition(*, organizer_id: uuid.UUID, status: str, title: str, slug: str | None = None) -> CompetitionModel:
    from apps.competitions.infrastructure.models import CompetitionModel

    return CompetitionModel.objects.create(
        organizer_id=organizer_id,
        status=status,
        title=title,
        season="2025/2026",
        slug=slug,
    )


def _locations(document: bytes) -> list[str]:
    """The <loc> values in a sitemap document.

    Takes the bytes rather than the response: that is all it parses, and the test
    client's response type is a private django-stubs alias no annotation should name.
    """
    root = ElementTree.fromstring(document)
    return [element.text or "" for element in root.findall("s:url/s:loc", _SITEMAP_NS)]


class TestRobotsTxt:
    def test_is_served_as_plain_text(self) -> None:
        response = Client().get("/robots.txt")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/plain")

    def test_points_the_crawler_at_the_sitemap(self) -> None:
        body = Client().get("/robots.txt").content.decode()

        assert "Sitemap: " in body
        assert body.rstrip().endswith("/sitemap.xml")

    @pytest.mark.parametrize(
        "path",
        ["/cabinet/", "/staff/", "/platform/", "/login", "/verify/", "/program/", "/protocol/", "/api/"],
    )
    def test_closes_every_private_and_personal_area(self, path: str) -> None:
        body = Client().get("/robots.txt").content.decode()

        assert f"Disallow: {path}" in body


class TestSitemap:
    def test_is_well_formed_xml(self) -> None:
        response = Client().get("/sitemap.xml")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/xml")
        # Parses at all: a malformed sitemap is silently discarded by crawlers.
        ElementTree.fromstring(response.content)

    def test_lists_the_public_static_pages(self) -> None:
        locations = _locations(Client().get("/sitemap.xml").content)

        assert any(location.endswith("/") for location in locations)
        assert any(location.endswith("/competitions") for location in locations)
        assert any(location.endswith("/privacy-policy") for location in locations)

    def test_lists_a_published_competition_by_its_readable_address(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, status="PUBLISHED", title="Весенний вокал", slug="vesenniy-vokal-2025-2026")

        locations = _locations(Client().get("/sitemap.xml").content)

        assert any(location.endswith("/competitions/vesenniy-vokal-2025-2026") for location in locations)

    def test_falls_back_to_the_id_when_a_competition_has_no_slug(self) -> None:
        # A row from before slugs existed: listed at the address that does resolve
        # rather than dropped from the map for lacking the prettier one.
        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="Старый фестиваль")

        locations = _locations(Client().get("/sitemap.xml").content)

        assert any(location.endswith(f"/competitions/{competition.id}") for location in locations)

    def test_never_lists_a_draft(self) -> None:
        # The whole point of generating this: a draft festival must not be handed
        # to a crawler, and a static file would have no way to know.
        org = _organization()
        _competition(organizer_id=org.id, status="DRAFT", title="Черновик", slug="chernovik")

        locations = _locations(Client().get("/sitemap.xml").content)

        assert not any("chernovik" in location for location in locations)

    def test_never_lists_a_soft_deleted_competition(self) -> None:
        from django.utils import timezone

        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="Удалённый", slug="udalenniy")
        competition.deleted_at = timezone.now()
        competition.save(update_fields=["deleted_at"])

        locations = _locations(Client().get("/sitemap.xml").content)

        assert not any("udalenniy" in location for location in locations)

    def test_every_location_is_absolute(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, status="PUBLISHED", title="Фестиваль", slug="festival-2025")

        locations = _locations(Client().get("/sitemap.xml").content)

        assert locations
        assert all(location.startswith("http://") or location.startswith("https://") for location in locations)

    def test_survives_a_title_that_produced_no_slug(self) -> None:
        # Guards the generator, not the slugger: an id-shaped fallback address is
        # still a valid <loc> and must not break the document for every other page.
        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="🎵")

        locations = _locations(Client().get("/sitemap.xml").content)

        assert any(str(competition.id) in location for location in locations)
        assert uuid.UUID(locations[-1].rsplit("/", 1)[-1])


class TestLlmsTxt:
    def test_is_served_as_plain_text(self) -> None:
        response = Client().get("/llms.txt")

        assert response.status_code == 200
        # Markdown under a .txt name: text/markdown makes a browser download it.
        assert response["Content-Type"].startswith("text/plain")

    def test_opens_with_the_site_name_and_a_summary(self) -> None:
        # The shape llmstxt.org specifies, and the part a reader short on context
        # keeps: one H1, then one blockquote saying what the site is.
        body = Client().get("/llms.txt").content.decode()
        lines = body.splitlines()

        assert lines[0] == "# Взлёт талантов"
        assert any(line.startswith("> ") for line in lines[:5])

    def test_links_the_public_pages_absolutely(self) -> None:
        body = Client().get("/llms.txt").content.decode()

        assert "## Основные страницы" in body
        assert "](http" in body
        for path in ("/competitions", "/privacy-policy", "/cookies"):
            assert f"{path})" in body

    def test_lists_a_published_competition_with_its_facts(self) -> None:
        from datetime import date

        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="Весенний вокал", slug="vesenniy-vokal")
        competition.competition_start = date(2026, 3, 12)
        competition.competition_end = date(2026, 3, 14)
        competition.save(update_fields=["competition_start", "competition_end"])

        body = Client().get("/llms.txt").content.decode()

        assert "[Весенний вокал](" in body
        assert "/competitions/vesenniy-vokal)" in body
        # Dates in ISO, like the sitemap's <lastmod>: the file is read by machines
        # first, and a dotted Russian date is a locale guess waiting to be wrong.
        assert "конкурс 2026-03-12 — 2026-03-14" in body
        assert "сезон 2025/2026" in body

    def test_never_lists_a_draft(self) -> None:
        # The reason this is generated at all: an unpublished competition must not
        # reach a model any more than it reaches a crawler.
        org = _organization()
        _competition(organizer_id=org.id, status="DRAFT", title="Черновик", slug="chernovik")

        body = Client().get("/llms.txt").content.decode()

        assert "chernovik" not in body
        assert "Черновик" not in body

    def test_never_lists_a_soft_deleted_competition(self) -> None:
        from django.utils import timezone

        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="Удалённый", slug="udalenniy")
        competition.deleted_at = timezone.now()
        competition.save(update_fields=["deleted_at"])

        body = Client().get("/llms.txt").content.decode()

        assert "udalenniy" not in body

    def test_names_no_page_that_carries_a_child(self) -> None:
        # The programme, the protocol and a diploma's verification link each name a
        # specific child. robots.txt closes them; this file must not hand them over
        # by another door.
        body = Client().get("/llms.txt").content.decode()

        assert "](http" in body
        for path in ("/program/", "/protocol/", "/verify/", "/cabinet/", "/staff/"):
            assert f"]({site_url()}{path}" not in body

    def test_says_so_when_nothing_is_published(self) -> None:
        # An empty heading reads as a failed fetch; a sentence reads as the truth.
        body = Client().get("/llms.txt").content.decode()

        assert "Пока не опубликовано ни одного мероприятия." in body

    def test_survives_a_title_holding_markdown_brackets(self) -> None:
        # Titles are typed into a form. Unescaped, this one would end the link label
        # early and turn the rest of the line into an address.
        org = _organization()
        _competition(organizer_id=org.id, status="PUBLISHED", title="Ритм [2026]", slug="ritm-2026")

        body = Client().get("/llms.txt").content.decode()
        line = next(line for line in body.splitlines() if "ritm-2026" in line)

        assert line.startswith("- [Ритм \\[2026\\]](")
        assert line.count("](") == 1
