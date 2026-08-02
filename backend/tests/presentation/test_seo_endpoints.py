"""Integration tests for ``robots.txt`` and ``sitemap.xml``.

These are the two documents a crawler reads before it reads the site, and both
are generated rather than shipped as files — so they are worth testing exactly
like an endpoint: what they list, and more importantly what they refuse to list.
"""

from __future__ import annotations

import uuid
from xml.etree import ElementTree

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

_SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _organization(name: str = "Дом талантов"):
    from apps.organization.infrastructure.models import OrganizationModel

    return OrganizationModel.objects.create(name=name, slug="dom-talantov")


def _competition(*, organizer_id, status: str, title: str, slug: str | None = None):
    from apps.competitions.infrastructure.models import CompetitionModel

    return CompetitionModel.objects.create(
        organizer_id=organizer_id,
        status=status,
        title=title,
        season="2025/2026",
        slug=slug,
    )


def _locations(response) -> list[str]:
    root = ElementTree.fromstring(response.content)
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
        locations = _locations(Client().get("/sitemap.xml"))

        assert any(location.endswith("/") for location in locations)
        assert any(location.endswith("/competitions") for location in locations)
        assert any(location.endswith("/privacy-policy") for location in locations)

    def test_lists_a_published_competition_by_its_readable_address(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, status="PUBLISHED", title="Весенний вокал", slug="vesenniy-vokal-2025-2026")

        locations = _locations(Client().get("/sitemap.xml"))

        assert any(location.endswith("/competitions/vesenniy-vokal-2025-2026") for location in locations)

    def test_falls_back_to_the_id_when_a_competition_has_no_slug(self) -> None:
        # A row from before slugs existed: listed at the address that does resolve
        # rather than dropped from the map for lacking the prettier one.
        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="Старый фестиваль")

        locations = _locations(Client().get("/sitemap.xml"))

        assert any(location.endswith(f"/competitions/{competition.id}") for location in locations)

    def test_never_lists_a_draft(self) -> None:
        # The whole point of generating this: a draft festival must not be handed
        # to a crawler, and a static file would have no way to know.
        org = _organization()
        _competition(organizer_id=org.id, status="DRAFT", title="Черновик", slug="chernovik")

        locations = _locations(Client().get("/sitemap.xml"))

        assert not any("chernovik" in location for location in locations)

    def test_never_lists_a_soft_deleted_competition(self) -> None:
        from django.utils import timezone

        org = _organization()
        competition = _competition(
            organizer_id=org.id, status="PUBLISHED", title="Удалённый", slug="udalenniy"
        )
        competition.deleted_at = timezone.now()
        competition.save(update_fields=["deleted_at"])

        locations = _locations(Client().get("/sitemap.xml"))

        assert not any("udalenniy" in location for location in locations)

    def test_every_location_is_absolute(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, status="PUBLISHED", title="Фестиваль", slug="festival-2025")

        locations = _locations(Client().get("/sitemap.xml"))

        assert locations
        assert all(location.startswith("http://") or location.startswith("https://") for location in locations)

    def test_survives_a_title_that_produced_no_slug(self) -> None:
        # Guards the generator, not the slugger: an id-shaped fallback address is
        # still a valid <loc> and must not break the document for every other page.
        org = _organization()
        competition = _competition(organizer_id=org.id, status="PUBLISHED", title="🎵")

        locations = _locations(Client().get("/sitemap.xml"))

        assert any(str(competition.id) in location for location in locations)
        assert uuid.UUID(locations[-1].rsplit("/", 1)[-1])
