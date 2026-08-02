"""The competition's readable public address, end to end.

A slug exists so the festival's URL carries its name into search results. That is
only worth anything if the address is *stable* — an organizer renaming a typo in
the title must not silently invalidate every link already printed on a poster —
and if the uuid form keeps resolving alongside it, because those links are
already in circulation.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _organization(name: str = "Дом талантов"):
    from apps.organization.infrastructure.models import OrganizationModel

    return OrganizationModel.objects.create(name=name, slug="dom-talantov")


def _competition(*, organizer_id, title: str, status: str = "PUBLISHED", **extra):
    from apps.competitions.infrastructure.models import CompetitionModel

    return CompetitionModel.objects.create(
        organizer_id=organizer_id,
        status=status,
        title=title,
        season="2025/2026",
        **extra,
    )


class TestResolvingACompetition:
    def test_resolves_by_slug(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        response = APIClient().get("/api/v1/public/festivals/vesenniy-vokal-2026")

        assert response.status_code == 200
        assert response.data["data"]["title"] == "Весенний вокал"

    def test_still_resolves_by_uuid(self) -> None:
        # Every link handed out before slugs existed — emailed, printed, bookmarked.
        org = _organization()
        competition = _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 200
        assert response.data["data"]["slug"] == "vesenniy-vokal-2026"

    def test_reports_the_slug_in_the_catalog(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        response = APIClient().get("/api/v1/public/festivals")

        assert response.data["data"][0]["slug"] == "vesenniy-vokal-2026"

    def test_a_competition_without_a_slug_reports_null_rather_than_failing(self) -> None:
        org = _organization()
        _competition(organizer_id=org.id, title="Старый фестиваль")

        response = APIClient().get("/api/v1/public/festivals")

        assert response.status_code == 200
        assert response.data["data"][0]["slug"] is None

    def test_an_unknown_slug_is_a_404_not_a_500(self) -> None:
        assert APIClient().get("/api/v1/public/festivals/net-takogo").status_code == 404

    def test_a_draft_does_not_leak_through_its_slug(self) -> None:
        # Same rule the uuid form obeys: an unpublished competition does not exist
        # as far as the public edge is concerned, whichever address is tried.
        org = _organization()
        _competition(organizer_id=org.id, title="Черновик", status="DRAFT", slug="chernovik")

        assert APIClient().get("/api/v1/public/festivals/chernovik").status_code == 404

    def test_the_registration_projection_accepts_the_slug_too(self) -> None:
        # Otherwise the readable URL renders a landing page whose registration
        # block can never load.
        org = _organization()
        _competition(organizer_id=org.id, title="Весенний вокал", slug="vesenniy-vokal-2026")

        response = APIClient().get("/api/v1/public/competitions/vesenniy-vokal-2026/registration")

        assert response.status_code == 200


class TestAssigningTheAddress:
    def _repository(self):
        from apps.competitions.infrastructure.repositories.django_competition_repository import (
            DjangoCompetitionRepository,
        )

        return DjangoCompetitionRepository()

    def _new_competition(self, *, title: str):
        from datetime import UTC, datetime

        from apps.competitions.domain.entities import Competition
        from apps.competitions.domain.value_objects import (
            CompetitionId,
            CompetitionTitle,
            OrganizerId,
            Season,
        )

        competition, _events = Competition.draft(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle(title),
            season=Season("2025/2026"),
            organizer_id=OrganizerId(uuid.uuid7()),
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        return competition

    def test_derives_an_address_from_the_title_on_insert(self) -> None:
        from apps.competitions.infrastructure.models import CompetitionModel

        competition = self._new_competition(title="Весенний вокал")
        self._repository().save(competition)

        row = CompetitionModel.objects.get(pk=competition.id.value)
        assert row.slug == "vesenniy-vokal-2025-2026"

    def test_numbers_a_second_competition_wanting_the_same_address(self) -> None:
        from apps.competitions.infrastructure.models import CompetitionModel

        repository = self._repository()
        first = self._new_competition(title="Весенний вокал")
        second = self._new_competition(title="Весенний вокал")
        repository.save(first)
        repository.save(second)

        assert CompetitionModel.objects.get(pk=second.id.value).slug == "vesenniy-vokal-2025-2026-2"

    def test_the_address_survives_a_rename(self) -> None:
        # The regression this file exists for: the mapper knows nothing about the
        # slug column, so a save that wrote every column back would blank it — and
        # the festival's public URL would 404 the moment anything else was edited.
        from datetime import UTC, datetime

        from apps.competitions.domain.value_objects import CompetitionTitle, Season
        from apps.competitions.infrastructure.models import CompetitionModel

        repository = self._repository()
        competition = self._new_competition(title="Весенний вокал")
        repository.save(competition)

        competition.update_general_information(
            now=datetime(2026, 2, 1, tzinfo=UTC),
            title=CompetitionTitle("Весенний вокал и танец"),
            season=Season("2025/2026"),
        )
        repository.save(competition)

        assert CompetitionModel.objects.get(pk=competition.id.value).slug == "vesenniy-vokal-2025-2026"
