"""Integration tests for the public Festival endpoints (participant-facing).

Driven through DRF's ``APIClient`` with **no** authentication — these are the
platform's only unauthenticated competition endpoints. The list catalog and the
single-competition landing detail are exercised end to end (reader → serializer →
``{data, meta}`` envelope / RFC 9457 problem).
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _organization(name: str = "Дом талантов"):
    from apps.organization.infrastructure.models import OrganizationModel

    return OrganizationModel.objects.create(name=name, slug="dom-talantov")


def _competition(*, organizer_id, status: str, title: str, **extra):
    from apps.competitions.infrastructure.models import CompetitionModel

    return CompetitionModel.objects.create(
        organizer_id=organizer_id,
        status=status,
        title=title,
        season="2025/2026",
        **extra,
    )


def _open_nomination(competition):
    """Seed a nomination with an open registration window (public status → REGISTRATION_OPEN)."""
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel

    return CategoryModel.objects.create(
        competition=competition,
        name="Vocal",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
    )


class TestPublicFestivalDetailEndpoint:
    def test_returns_landing_view_for_public_competition(self) -> None:
        org = _organization()
        competition = _competition(
            organizer_id=org.id,
            status="PUBLISHED",
            title="Весенний вокал",
            venue_name="Дворец культуры",
            contacts_config={
                "use_organization_contacts": False,
                "override": {"organization_name": "Оргкомитет", "website": "https://fest.by"},
                "venue_details": {"city": "Минск"},
            },
        )
        _open_nomination(competition)

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 200
        data = response.data["data"]
        assert data["title"] == "Весенний вокал"
        assert data["status"] == "REGISTRATION_OPEN"
        assert [block["type"] for block in data["landing"]["blocks"]] == [
            "HERO",
            "REGULATION",
            "DOCUMENTS",
            "VENUE",
        ]
        assert data["contacts"]["organizationName"] == "Оргкомитет"
        assert data["contacts"]["website"] == "https://fest.by"
        assert data["contacts"]["venue"]["name"] == "Дворец культуры"
        assert data["contacts"]["venue"]["city"] == "Минск"
        assert response["X-Request-ID"]

    def test_exposes_current_regulation(self) -> None:
        import datetime

        from apps.competitions.infrastructure.models import CompetitionModel, RegulationModel

        org = _organization()
        competition = _competition(
            organizer_id=org.id, status="PUBLISHED", title="Весенний фестиваль"
        )
        regulation = RegulationModel.objects.create(
            competition=competition,
            title="Положение фестиваля 2026",
            document_version="v2",
            publication_date=datetime.date(2026, 6, 1),
            file_reference="/media/regulations/fest-2026.pdf",
        )
        CompetitionModel.objects.filter(pk=competition.pk).update(
            current_regulation_id=regulation.id
        )

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 200
        assert response.data["data"]["regulation"] == {
            "title": "Положение фестиваля 2026",
            "version": "v2",
            "publicationDate": "2026-06-01",
            "fileReference": "/media/regulations/fest-2026.pdf",
        }

    def test_exposes_public_documents(self) -> None:
        from apps.competitions.infrastructure.models import DocumentModel

        org = _organization()
        competition = _competition(
            organizer_id=org.id, status="PUBLISHED", title="Фестиваль документов"
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Программа фестиваля",
            category="PROGRAM",
            visibility="PUBLIC",
            file_reference="/media/program.pdf",
            description="Расписание по дням",
            published=True,
            sort_order=0,
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Служебная записка",
            category="MEMO",
            visibility="STAFF",
            file_reference="/media/staff.pdf",
            published=True,
            sort_order=1,
        )

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 200
        documents = response.data["data"]["documents"]
        assert [doc["title"] for doc in documents] == ["Программа фестиваля"]
        assert documents[0]["fileReference"] == "/media/program.pdf"
        assert documents[0]["description"] == "Расписание по дням"

    def test_regulation_is_null_when_absent(self) -> None:
        org = _organization()
        competition = _competition(
            organizer_id=org.id, status="PUBLISHED", title="Без положения"
        )

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 200
        assert response.data["data"]["regulation"] is None

    def test_hidden_state_is_404_problem(self) -> None:
        org = _organization()
        competition = _competition(organizer_id=org.id, status="DRAFT", title="Черновик")

        response = APIClient().get(f"/api/v1/public/festivals/{competition.id}")

        assert response.status_code == 404
        assert response["Content-Type"].startswith("application/problem+json")
        assert response.data["code"] == "festival_not_found"

    def test_missing_id_is_404(self) -> None:
        response = APIClient().get(f"/api/v1/public/festivals/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_malformed_id_is_404_not_500(self) -> None:
        response = APIClient().get("/api/v1/public/festivals/not-a-uuid")

        assert response.status_code == 404
